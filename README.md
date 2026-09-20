# My RSS — 自分用の汎用RSSメーカー

公開ページの記事一覧をRSSに変換し、GitHub Actionsで毎時更新、GitHub Pagesで公開します。公開後はPCを起動しておく必要はありません。ログイン情報・APIキー・外部サーバー契約は不要です。

**まず「1. GitHubへアップロード」→「2. 公開設定」→「3. Inoreaderへ登録」を順に行ってください。** このZIPをダウンロードしただけでは自動更新・公開は始まりません。

## 対象サイトと確認結果

2026年9月20日に、実際の公開HTML取得とRSS生成を確認しました。

| サイト | このツールの設定 | 既存RSSの確認 |
|---|---|---|
| AimanaVo | `sites/aimanavo.json` → `docs/aimanavo.xml` | HTMLのRSS/Atom宣言と代表的URLを調査した範囲では未発見 |
| GameMakers | `sites/gamemakers.json` → `docs/gamemakers.xml` | **公式RSSが正常に取得できました。下記URLを優先利用できます** |
| ファミ通.com | `sites/famitsu.json` → `docs/famitsu.xml` | RSSHubルートの案内はありますが公開サーバーは今回403。代替として自前生成を同梱 |

GameMakers公式RSS： **https://gamemakers.jp/feed/**

検証時はRSS 2.0、30記事、最新記事の日付は2026年9月19日でした。以前の会話で「取得できなかった」とされたURLですが、今回の直接取得では使えました。要件に合わせて自前生成設定も残しています。公式と自前の両方を購読すると記事が重複するので、どちらか片方を登録してください。

ファミ通のRSSHub候補： **https://rsshub.app/famitsu/category/new-article**

[RSSHubのルート案内](https://rsshub-doc.pages.dev/en/game#ファミ通)には `/famitsu/category/:category?` が掲載されています。ただしこの文書は古く、現在の公開インスタンスではHTTP 403でした。**ルート掲載＝現在の稼働保証ではありません。** InoreaderでこのURLを試し、新しい記事が読めた場合はそちらを利用できます。失敗する場合は同梱の `famitsu.xml` を利用してください。

## 1. GitHubへアップロードする（初回のみ）

### おすすめ：GitHub Desktopでアップロード

プログラミングやコマンド入力なしで一式をアップロードできます。

1. [GitHub](https://github.com/)のアカウントを作成します。
2. [GitHub Desktop](https://desktop.github.com/)をインストールし、GitHubにサインインします。
3. ダウンロードしたZIPを右クリックし「すべて展開」。中にある `my-rss` フォルダを開きます。
4. GitHub Desktopで **File → New repository** を選び、Nameを `my-rss` にします。Local pathは、展開した場所とは別の保存先にします。「Initialize this repository with a README」にチェックして **Create repository**。
5. GitHub Desktopの **Repository → Show in Explorer** で新しいリポジトリのフォルダを開きます。
6. ZIPから展開した `my-rss` の**中身をすべて**、手順5のフォルダへコピーします。READMEの上書きは許可します。`my-rss` フォルダ自体を入れて二重にしないでください。
7. `.github` と `.gitignore` も含めます。見えない場合はエクスプローラーの **表示 → 表示 → 隠しファイル** をオンにします。
8. GitHub Desktopへ戻り、Summaryに `Add RSS tool` と書いて **Commit to main**。
9. **Publish repository** を押し、**Keep this code private のチェックを外して**公開リポジトリにします。もう一度 **Publish repository**。
10. ブラウザーでリポジトリを開き、先頭に `README.md`、`generate.py`、`sites`、`docs`、`.github` が並んでいることを確認します。

GitHub Freeの公開リポジトリを想定しています。生成したRSS・取得履歴も公開されます。会員限定記事や認証情報を設定ファイルに入れる構成ではありません。

### ブラウザーだけでアップロードする場合

1. GitHubの **＋ → New repository** で名前 `my-rss`、**Public**、READMEを追加する設定で作成します。ブランチ名は `main` にしてください。
2. **Add file → Upload files** で、ZIPから展開したフォルダの中身をアップロードし、**Commit changes**。
3. `.github` フォルダがアップロードされなかった場合は、**Add file → Create new file** を選びます。ファイル名を `.github/workflows/update-feeds.yml` にして、同梱ファイルの中身を丸ごと貼り付けて保存します。
4. リポジトリの直下に `generate.py` があり、`.github/workflows/update-feeds.yml` が存在することを確認します。

## 2. ActionsとPagesを設定する

1. リポジトリの **Settings → Actions → General** を開きます。Actionsが無効なら許可します。利用Actionを制限している場合は `actions/*` を許可してください。
2. 同じ画面の **Workflow permissions** で **Read and write permissions** を選び、**Save**。RSS履歴をリポジトリへ保存するための権限です。
3. **Settings → Pages → Build and deployment → Source** を **GitHub Actions** にします。
   - `Deploy from a branch` や `main /docs` は選びません。この一式は、生成した `docs/` をActionsから直接配信する方式です。
   - 提案される別のワークフローを追加する必要はありません。
4. **Actions** タブを開きます。実行許可の案内が出たら有効にします。
5. 左の **Update RSS and publish → Run workflow → main → Run workflow** を押します。
6. 数分待ち、実行結果が緑色になったことを確認します。最初のアップロード直後、Pages設定前の実行が失敗していても、設定後に再実行すれば大丈夫です。
7. **Settings → Pages** に表示されたURLを開きます。通常は次の形です。

```text
https://あなたのGitHubユーザー名.github.io/my-rss/
```

「My RSS」と各サイトのRSSリンク、取得結果が表示されれば公開できています。

**以後は毎時17分を目安に更新されます。** GitHubの混雑で遅れる場合があります。時刻指定はUTCですが、毎時実行なので日本時間でも毎時17分です。Inoreaderの巡回にも別途時間がかかります。

## 3. Inoreaderへ登録する

1. 公開した「My RSS」ページで、AimanaVoの「RSSを開く」を右クリックし **リンクのアドレスをコピー**。
2. Inoreaderで **Add feed（＋／フィードを追加）** を開きます。
3. コピーしたURLを入力して検索し、表示されたフィードを **Follow／購読** します。既に生成済みのRSSなので、Web feed／Track changes機能ではなく、通常のフィード追加を使います。
4. GameMakers、ファミ通も同様に登録します。GameMakersは公式RSSを直接登録しても構いません。

自前生成URLの例（ユーザー名は置き換えてください）：

```text
https://YOURNAME.github.io/my-rss/aimanavo.xml
https://YOURNAME.github.io/my-rss/gamemakers.xml
https://YOURNAME.github.io/my-rss/famitsu.xml
```

`github.com/.../blob/...` のURLではなく、**公開先の `github.io` のURL**を登録します。ブラウザーでXMLの文字が表示されるのは正常です。

## 4. 新しいサイトを追加する

### 先に普通のRSS/Atomを探す（任意）

Python 3.12以降が入ったPCで、フォルダをターミナルで開いて実行できます。

```console
python -m pip install -r requirements.txt
python generate.py --discover https://example.com/news/
```

ページ内のRSS/Atom宣言と `/feed/`、`/rss.xml`、`/atom.xml`、`/feed.xml` を確認し、実際にRSS/AtomのXMLだったURLだけを表示します。見つかったURLはInoreaderへ直接登録できます。`[]` は調査範囲内で見つからなかった意味で、存在しないことを保証するものではありません。更新が止まった古いRSSでないかも確認してください。

この機能は**検出専用**です。生成元を自動で変更したり、RSSHubの全ルートを検索したりはしません。

### RSSがない場合：JSONを1つ追加

1. リポジトリをブラウザーで開いて **Add file → Create new file**。
2. 名前を `sites/example.json` にします。`example` は好きな半角英小文字・数字・`-`・`_` に変更できます。
3. 同梱の `examples/site.json` を貼り付け、URLとセレクタを対象サイトに合わせます。
4. **Commit changes** で `main` に保存すると、自動で取得・公開されます。
5. 公開ページで取得成功を確認し、新しいRSSリンクをInoreaderへ登録します。

例えば次のHTMLなら、同梱のサンプル設定を使えます。

```html
<article>
  <h2><a href="/news/123">新しい記事のタイトル</a></h2>
  <time datetime="2026-09-20T10:00:00+09:00">2026年9月20日</time>
  <p class="summary">記事の短い説明</p>
</article>
```

```json
{
  "name": "サンプルニュース",
  "url": "https://example.com/news/",
  "item_selector": "article",
  "title": {"selector": "h2 a"},
  "link": {"selector": "h2 a", "attribute": "href"},
  "date": {"selector": "time", "attribute": "datetime"},
  "summary": {"selector": ".summary"},
  "timezone": "Asia/Tokyo",
  "max_items": 100
}
```

| 設定 | 意味 |
|---|---|
| `name` | Inoreaderに表示する名前 |
| `url` | 記事が並んでいる公開ページ |
| `item_selector` | 記事1件を囲む要素のCSSセレクタ |
| `title` | 各記事要素の中のタイトル |
| `link` | 各記事要素の中のリンク。通常は `attribute: href` |
| `date` | 任意。日時要素。ISO 8601やRFC形式に対応 |
| `date_format` | 任意。`2026.09.20` なら `%Y.%m.%d`、`2026/09/20` なら `%Y/%m/%d` |
| `summary` | 任意。概要要素。最大500文字のプレーンテキスト |
| `timezone` | タイムゾーンのない日時の解釈。既定は `Asia/Tokyo` |
| `max_items` | 今までに取得した記事を残す上限。既定100件、正の整数 |
| `url_pattern` | 任意。記事URLを限定する正規表現。JSON内の `\` は `\\` と記述 |
| `fallback` | 任意。通常の抽出が0件だったときに試す別の抽出設定 |
| `enabled` | `false` にすると更新対象から除外 |

`title` などの `selector` は記事要素からの相対指定です。記事要素自体を使うときは `:scope`。`attribute` を省くと要素内の文字を取り出します。日付や概要がないサイトでは、その設定行を削除できます。JSONにはコメントや末尾の余分なカンマを書けません。

CSSセレクタはブラウザーで記事タイトルを右クリックして **検証** から調べます。`article` はタグ名、`.summary` はクラス名、`h2 a` はh2の中のリンクです。サイトごとに構造が違うため、URLだけで全サイトを正確に自動設定する機能はありません。分からない場合は対象URLと `examples/site.json` を添えて設定作成を依頼してください。

### 更新を止めたい／削除したい場合

該当JSONに `"enabled": false` を追加すると更新を止められます。過去のXMLと履歴は残ります。完全に消す場合はJSONに加え、対応する `docs/名前.xml` と `docs/_state/名前.json` も削除し、Actionsを手動実行してください。

## 取得内容と制約

- サムネイル画像に対応しています。RSS本文の画像と `media:thumbnail` に元サイトの画像URLを含めます。画像ファイル自体は複製せず、元サイトから読み込みます。
- 追加サイトでは `"image": {"selector": "img", "attribute": "src"}` を指定できます。遅延読み込み画像なら `attribute` を `data-src` などに変更します。
- 画像が記事要素の外にある場合は `"image_from_link": {"selector": "img", "attribute": "src"}` で、同じ記事URLにリンクする画像を一覧内から探せます。
- 画像のない記事・過去に一覧から消えた記事は画像なしのままです。Inoreaderに取り込み済みの記事は、本文変更が反映されない場合があります。新着記事で確認してください。

- AimanaVo：現在の `article.tl-item` 内の見出し・概要を取得。検証時7記事。「もっと読み込む」以降や過去の全記事は取得しません。
- GameMakers：現在の `.l-home-article` から見出し・日付を取得。検証時30記事。概要のない一覧なのでRSS本文は空欄です。公開時刻までは分からないため、その日の日本時間0時として扱います。
- ファミ通：新着1ページ目の一覧から見出し・リンクを取得。検証時50記事。日付は相対表記なので初回取得日時を使います。
- AimanaVoも絶対日時がないため初回取得日時を使います。**RSSの日付は元記事の正確な公開日時とは限りません。** 保存した日時は次の実行で変更しません。
- 記事URLをGUIDにして重複を防ぎ、一覧から消えた記事も100件まで保持します。`docs/_state/` が保存先です。削除すると初回取得日時がリセットされます。
- 1時間の間に一覧から押し出された記事、停止期間中の記事は取り逃す可能性があります。過去記事の完全収集ツールではありません。
- ログイン・有料本文・JavaScript実行が必要なサイトにはそのまま対応しません。公開HTMLに記事が存在するサイトが対象です。
- 0件・HTTPエラーでは前回のRSSを残し、他サイトは更新します。公開ページに失敗内容を表示し、Actionsも失敗として通知できるようにしています。
- フォールバックを使ったときは公開ページに要確認と表示します。サイトの大幅な改修ではJSONの修正が必要です。

## 困ったとき

| 症状 | 確認するところ |
|---|---|
| Actionsタブに処理がない | `.github/workflows/update-feeds.yml` が直下からの正しいパスにあるか。ブランチ名が `main` か |
| Pagesが404 | Sourceが **GitHub Actions** か。実行が成功したか。公開後数分待ったか |
| `git push` が403 | ActionsのRead and write permissions、組織の制限、mainのブランチ保護を確認 |
| `git push` がreject | 実行中に別の変更が入った可能性。Actionsから再実行。履歴保存前の失敗なので、その回は公開されません |
| `0 articles extracted` | HTML構造変更、ログイン要求、アクセス制限。該当サイトのセレクタを確認 |
| `HTTP Error 403/429` | 相手側のアクセス制限。時間を空けるか公式RSSを利用。制限回避は実装していません |
| 新着が遅い | Actionsの実行時刻、公開ページの最終実行日時、Inoreaderの巡回間隔を確認 |
| 定期実行が止まった | GitHubは公開リポジトリが60日間非活動の場合、スケジュールを無効化することがあります。Actions画面で再有効化し、手動実行 |
| 日付が取得時刻になる | 元ページに絶対日時がないか、`date_format` が一致していません。公開ページの警告も確認 |

スケジュールは厳密な時刻保証ではありません。GitHubからのActions失敗通知を受け取れる設定にしておくと、取得元の変更に気付きやすくなります。

## PCで試す場合（任意）

通常運用にPCのPythonは不要です。自分で設定を検証したい場合だけ、Python 3.12以降で実行します。

```console
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python generate.py
```

`docs/index.html` を開くと取得結果を確認できます。ローカルファイルをInoreaderに登録することはできません。上記のPages公開が必要です。

## ファイル構成

```text
my-rss/
  .github/workflows/update-feeds.yml  定期実行・履歴保存・Pages公開
  sites/*.json                       サイトごとの設定
  examples/site.json                 追加用ひな形
  generate.py                        汎用抽出・RSS生成・検出
  requirements.txt                   Python依存ライブラリ
  tests/test_generate.py             重複・日付・失敗保持などのテスト
  docs/*.xml                         配信用RSS
  docs/_state/*.json                 日時と過去記事の保持
  docs/status.json                   直近の実行結果
  docs/index.html                    RSSリンク一覧
```

## 参考リンク

- [GitHub Desktopでの初回リポジトリ作成](https://docs.github.com/en/desktop/overview/creating-your-first-repository-using-github-desktop)
- [GitHub Pagesの公開元設定](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [GitHub Actionsのschedule仕様](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Inoreaderのフィード追加](https://www.inoreader.com/blog/2024/11/getting-started-with-inoreader.html)

同梱XMLは検証時に生成したものです。あなたのGitHub上でのActions実行・Pages公開・Inoreaderでの受信確認は、初回設定後に行ってください。
