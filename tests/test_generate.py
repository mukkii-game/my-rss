import json
from pathlib import Path
from contextlib import contextmanager
import shutil
import uuid
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import generate as g


@contextmanager
def test_directory():
    base = Path.cwd().resolve()
    target = base / ('test-work-' + uuid.uuid4().hex)
    target.mkdir(mode=0o755)
    try:
        yield target
    finally:
        if target.resolve().parent != base:
            raise RuntimeError('Unexpected temporary directory')
        shutil.rmtree(target)


class GeneratorTests(unittest.TestCase):
    def test_images_extraction_rendering_and_history(self):
        c = self.config()
        c['image'] = {'selector': 'img', 'attribute': 'data-src'}
        html = '<article><h2>A &quot;B&quot;</h2><a href="/1">open</a><img data-src="/photo.jpg?a=1&amp;b=2"></article>'
        items, _ = g.extract(html, c, c['url'])
        self.assertEqual(items[0]['image'], 'https://example.com/photo.jpg?a=1&b=2')
        merged = g.merge([], items, '2026-09-20T00:00:00+00:00', 100)
        entry = ET.fromstring(g.rss_bytes(c, merged)).find('channel/item')
        self.assertEqual(entry.find('{'+g.MEDIA_NS+'}thumbnail').get('url'), items[0]['image'])
        self.assertIn('alt="A &quot;B&quot;"', entry.findtext('description'))
        self.assertIn('a=1&amp;b=2', entry.findtext('description'))
        items[0]['image'] = ''
        self.assertEqual(g.merge(merged, items, '2026-09-21T00:00:00+00:00', 100)[0]['image'], merged[0]['image'])
        bad, _ = g.extract(html.replace('/photo.jpg?a=1&amp;b=2', 'javascript:alert(1)'), c, c['url'])
        self.assertEqual(bad[0]['image'], '')

    def test_image_matched_by_article_url(self):
        c = self.config()
        c['image_from_link'] = {'selector': 'img', 'attribute': 'src'}
        html = '<a href="/1"><img src="//cdn.example.com/photo.jpg"></a><article><h2>A</h2><a href="/1">open</a></article>'
        items, _ = g.extract(html, c, c['url'])
        self.assertEqual(items[0]['image'], 'https://cdn.example.com/photo.jpg')

    def config(self):
        return {'name': 'Test & news', 'url': 'https://example.com/news',
                'item_selector': 'article', 'title': {'selector': 'h2'},
                'link': {'selector': 'a', 'attribute': 'href'},
                'summary': {'selector': 'p'}}

    def test_relative_urls_dedup_and_unsafe_links(self):
        html = '<article><h2>A &amp; B</h2><a href="/1#part">open</a><p>&lt;b&gt;text&lt;/b&gt;</p></article>'
        html += html + '<article><h2>Bad</h2><a href="javascript:alert(1)">x</a></article>'
        items, _ = g.extract(html, self.config(), 'https://example.com/news')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['link'], 'https://example.com/1')
        result = g.merge([], items, '2026-09-20T00:00:00+00:00', 100)
        root = ET.fromstring(g.rss_bytes(self.config(), result))
        self.assertEqual(root.findtext('channel/item/title'), 'A & B')
        self.assertEqual(root.findtext('channel/item/description'), '&lt;b&gt;text&lt;/b&gt;')

    def test_dates_timezone_and_invalid(self):
        self.assertEqual(g.parse_date('2026.09.20', {'date_format': '%Y.%m.%d'}), '2026-09-19T15:00:00+00:00')
        self.assertEqual(g.parse_date('2026-09-20T12:00:00+09:00', {}), '2026-09-20T03:00:00+00:00')
        self.assertIsNone(g.parse_date('2時間前', {}))

    def test_stable_dates_and_history(self):
        a = {'title': 'A', 'link': 'https://example.com/a', 'published': None}
        b = {'title': 'B', 'link': 'https://example.com/b', 'published': None}
        old = g.merge([], [a], '2026-09-19T00:00:00+00:00', 100)
        new = g.merge(old, [a, b], '2026-09-20T00:00:00+00:00', 100)
        self.assertEqual(new[1]['published'], old[0]['published'])
        self.assertEqual(g.merge(new, [b], '2026-09-21T00:00:00+00:00', 100), new)
        self.assertEqual(len(g.merge(new, [], '', 1)), 1)

    def test_fallback_and_zero_items(self):
        c = self.config()
        c['fallback'] = {'item_selector': 'h3 a', 'title': {'selector': ':scope'},
                         'link': {'selector': ':scope', 'attribute': 'href'}}
        items, warnings = g.extract('<h3><a href="/x">X</a></h3>', c, c['url'])
        self.assertEqual(items[0]['title'], 'X')
        self.assertTrue(warnings)
        with self.assertRaises(ValueError):
            g.extract('<html>Access denied</html>', c, c['url'])

    def test_partial_failure_keeps_previous_rss(self):
        with test_directory() as d:
            root = Path(d)
            sites, out = root / 'sites', root / 'docs'
            sites.mkdir()
            for name in ['a', 'b']:
                (sites / (name + '.json')).write_text(json.dumps(self.config()), encoding='utf-8')
            good = '<article><h2>A</h2><a href="/a">A</a></article>'
            with patch.object(g, 'fetch', return_value=(good, 'https://example.com')):
                self.assertEqual(g.build(sites, out), 0)
            previous = (out / 'a.xml').read_bytes()
            with patch.object(g, 'fetch', side_effect=[RuntimeError('HTTP 403'), (good, 'https://example.com')]):
                self.assertEqual(g.build(sites, out), 1)
            self.assertEqual((out / 'a.xml').read_bytes(), previous)
            status = json.loads((out / 'status.json').read_text(encoding='utf-8'))
            self.assertFalse(status[0]['ok'])
            self.assertTrue(status[1]['ok'])

    def test_discovery_validates_xml(self):
        def fake(url):
            if url.endswith('/news'):
                return '<link rel="alternate" type="application/atom+xml" href="/atom">', url
            if url.endswith('/atom'):
                return '<feed xmlns="http://www.w3.org/2005/Atom"><title>T</title></feed>', url
            return '<html>Not a feed</html>', url
        with patch.object(g, 'fetch', side_effect=fake):
            self.assertEqual(g.discover('https://example.com/news'), [{'url': 'https://example.com/atom', 'type': 'feed'}])


if __name__ == '__main__':
    unittest.main()
