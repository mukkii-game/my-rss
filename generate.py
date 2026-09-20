"""Config-driven, public-HTML RSS generator. Python 3.12+."""
import argparse
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from html import escape
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlsplit, urlunsplit
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent


def fetch(url):
    if urlsplit(url).scheme not in ('http', 'https'):
        raise ValueError('HTTP(S) URL required')
    request = Request(url, headers={'User-Agent': 'PersonalRSS/1.0 (+public headlines; hourly)'})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=25) as r:
                data = r.read(8_000_001)
                if len(data) > 8_000_000:
                    raise ValueError('Page exceeds 8 MB')
                return data.decode(r.headers.get_content_charset() or 'utf-8'), r.url
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def canonical(url):
    p = urlsplit(url)
    if p.scheme not in ('http', 'https') or not p.netloc:
        return ''
    return urlunsplit((p.scheme, p.netloc, p.path, p.query, ''))


def field(node, spec):
    if not spec:
        return ''
    selector = spec.get('selector', ':scope')
    target = node if selector == ':scope' else node.select_one(selector)
    if target is None:
        return ''
    value = target.get(spec['attribute'], '') if spec.get('attribute') else target.get_text(' ', strip=True)
    return ' '.join(str(value).split())


def parse_date(value, config):
    if not value:
        return None
    try:
        if config.get('date_format'):
            dt = datetime.strptime(value, config['date_format'])
        else:
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(config.get('timezone', 'Asia/Tokyo')))
        return dt.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def extract(html, config, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    warnings = []
    for attempt, selectors in enumerate([config, config.get('fallback', {})]):
        if not selectors.get('item_selector'):
            continue
        items = {}
        missing_dates = 0
        for node in soup.select(selectors['item_selector']):
            title = field(node, selectors.get('title'))
            raw_link = field(node, selectors.get('link'))
            link = canonical(urljoin(base_url, raw_link)) if raw_link else ''
            if not title or not link or (config.get('url_pattern') and not re.search(config['url_pattern'], link)):
                continue
            date = parse_date(field(node, selectors.get('date')), config)
            if selectors.get('date') and not date:
                missing_dates += 1
            items.setdefault(link, {'title': title, 'link': link,
                'summary': field(node, selectors.get('summary'))[:500], 'published': date})
        if items:
            if attempt:
                warnings.append('Fallback selectors used; check site structure.')
            if missing_dates:
                warnings.append(f'{missing_dates} dates missing/unparseable; using first seen time.')
            return list(items.values()), warnings
    raise ValueError('0 articles extracted; previous RSS retained. Check selectors / access restrictions.')


def merge(old, new, now, limit):
    known = {i['link']: dict(i) for i in old}
    for item in new:
        previous = known.get(item['link'], {})
        value = dict(item)
        value['first_seen'] = previous.get('first_seen', now)
        value['published'] = previous.get('published') or item.get('published') or value['first_seen']
        if not value.get('summary'):
            value['summary'] = previous.get('summary', '')
        known[item['link']] = value
    return sorted(known.values(), key=lambda x: x['published'], reverse=True)[:limit]


def clean_xml(value):
    return re.sub('[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]', '', str(value))


def rss_bytes(config, items):
    root = ET.Element('rss', version='2.0')
    channel = ET.SubElement(root, 'channel')
    def add(parent, name, value, **attrs):
        ET.SubElement(parent, name, attrs).text = clean_xml(value)
    add(channel, 'title', config['name'])
    add(channel, 'link', config['url'])
    add(channel, 'description', config.get('description', config['name'] + ' 非公式RSS'))
    add(channel, 'language', 'ja')
    add(channel, 'ttl', '60')
    for item in items:
        entry = ET.SubElement(channel, 'item')
        add(entry, 'title', item['title'])
        add(entry, 'link', item['link'])
        add(entry, 'guid', item['link'], isPermaLink='true')
        # Description is HTML in RSS: escape untrusted text before XML serialization.
        add(entry, 'description', escape(item.get('summary', '')))
        add(entry, 'pubDate', format_datetime(datetime.fromisoformat(item['published'])))
    ET.indent(root)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_bytes(data)
    temp.replace(path)


def write_json(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def feed_kind(text):
    try:
        root = ET.fromstring(text.lstrip('\ufeff').encode('utf-8'))
        name = root.tag.rsplit('}', 1)[-1]
        return name if name in ('rss', 'feed', 'RDF') else None
    except ET.ParseError:
        return None


def discover(url):
    html, base = fetch(url)
    if feed_kind(html):
        return [{'url': base, 'type': feed_kind(html)}]
    soup = BeautifulSoup(html, 'html.parser')
    candidates = [urljoin(base, n['href']) for n in soup.select('link[href]')
                  if n.get('type', '').split(';')[0] in ('application/rss+xml', 'application/atom+xml', 'application/rdf+xml')]
    candidates += [urljoin(base, path) for path in ['/feed/', '/rss.xml', '/atom.xml', '/feed.xml']]
    found = []
    for candidate in dict.fromkeys(candidates):
        try:
            body, final_url = fetch(candidate)
            kind = feed_kind(body)
            if kind and not any(x['url'] == final_url for x in found):
                found.append({'url': final_url, 'type': kind})
        except (URLError, TimeoutError, UnicodeError, ValueError):
            pass
    return found


def build(sites_dir, output):
    configs = sorted(sites_dir.glob('*.json'))
    if not configs:
        raise ValueError('No sites/*.json found')
    status = []
    errors = 0
    now = datetime.now(timezone.utc).isoformat()
    for path in configs:
        slug = path.stem
        if not re.fullmatch(r'[a-z0-9_-]+', slug):
            raise ValueError('Use lowercase ASCII site filenames: ' + path.name)
        record = {'id': slug, 'name': slug, 'checked_at': now}
        rss_path = output / (slug + '.xml')
        state_path = output / '_state' / (slug + '.json')
        try:
            config = json.loads(path.read_text(encoding='utf-8-sig'))
            if config.get('enabled', True) is False:
                continue
            record['name'] = config['name']
            limit = config.get('max_items', 100)
            if type(limit) is not int or limit < 1:
                raise ValueError('max_items must be a positive integer')
            html, base = fetch(config['url'])
            fresh, warnings = extract(html, config, base)
            old = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else []
            items = merge(old, fresh, now, limit)
            if not items:
                raise ValueError('max_items must be positive')
            atomic_write(rss_path, rss_bytes(config, items))
            write_json(state_path, items)
            record.update(ok=True, fetched=len(fresh), retained=len(items), warnings=warnings)
            print(f'{slug}: {len(fresh)} extracted / {len(items)} retained', flush=True)
        except Exception as error:
            errors += 1
            record.update(ok=False, error=str(error))
            print(f'{slug}: ERROR: {error}', file=sys.stderr, flush=True)
        record['feed'] = rss_path.name if rss_path.exists() else None
        status.append(record)
    write_json(output / 'status.json', status)
    rows = []
    for s in status:
        link = f'<a href="{escape(s["feed"])}">RSSを開く</a>' if s['feed'] else 'RSS未生成'
        message = ('取得成功（' + str(s['fetched']) + '件）' + ('・要確認: ' + '; '.join(s['warnings']) if s['warnings'] else '')) if s['ok'] else '更新失敗・前回分を保持: ' + s['error']
        rows.append(f'<li><h2>{escape(s["name"])}</h2>{link}<p>{escape(message)}</p></li>')
    page = '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>My RSS</title><style>body{font:17px/1.7 system-ui;max-width:850px;margin:50px auto;padding:0 24px;background:#f5f7fb;color:#182235}li{background:white;padding:18px 28px;margin:20px 0;border-radius:12px}ul{padding:0;list-style:none}a{color:#1655bd}h2{margin-top:0}</style><h1>My RSS</h1><p>RSSリンクのアドレスをコピーし、Inoreaderへ登録してください。</p><p>最終実行（UTC）: ' + escape(now) + '</p><ul>' + ''.join(rows) + '</ul><p>各サイトの公開情報から作成した非公式RSSです。</p></html>'
    atomic_write(output / 'index.html', page.encode('utf-8'))
    atomic_write(output / '.nojekyll', b'')
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--discover', metavar='URL', help='Find and validate RSS/Atom URLs; no files changed')
    parser.add_argument('--sites', type=Path, default=ROOT / 'sites')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs')
    args = parser.parse_args()
    if args.discover:
        print(json.dumps(discover(args.discover), ensure_ascii=False, indent=2))
        return 0
    return build(args.sites, args.output)


if __name__ == '__main__':
    sys.exit(main())
