[README.md](https://github.com/user-attachments/files/27244331/README.md)
# Heddmann Watch

[heddmann.com](https://www.heddmann.com/) の「お知らせ」欄を監視し、更新されたら LINE に通知する仕組み。GitHub Actions 上で 15 分ごとに自動実行されます。

## 仕組み

1. GitHub Actions が cron で `watch.py` を起動
2. heddmann.com のトップページを取得（EUC-JP デコード）
3. 「お知らせ」欄の **最新日付** を正規表現で抽出
4. 前回保存した日付（`last_seen.json`）と比較
5. 違っていたら LINE Messaging API で push 通知
6. 新しい日付を `last_seen.json` に保存してリポジトリに commit

商品リストの差分を取るより、お知らせ欄の日付を見るほうが誤検知が少なく確実です。

---

## セットアップ手順

### 1. LINE Messaging API の準備

#### 1-1. LINE Developers にログイン

[https://developers.line.biz/](https://developers.line.biz/) にアクセスし、自分の LINE アカウントでログイン。

#### 1-2. プロバイダーを作成

「Create a new provider」→ 適当な名前（例: `personal-watcher`）で作成。

#### 1-3. Messaging API チャネルを作成

プロバイダー画面で「Create a Messaging API channel」を選択。

入力項目：
- Channel name: `Heddmann Watcher`（後で LINE 上の Bot 名になります）
- Channel description: 任意
- Category / Subcategory: 任意（個人用なので何でも可）
- それ以外はデフォルトで OK

作成すると LINE 公式アカウントが自動的にできます。

#### 1-4. 公式アカウント設定（重要）

[LINE Official Account Manager](https://manager.line.biz/) で作成した Bot を開き、**「応答設定」** タブで以下に設定：

- 応答メッセージ: **オフ**
- あいさつメッセージ: **オフ**（任意）
- Webhook: **オン**（次の手順で UserId を取るときだけ）

これをやっておかないと、自分が Bot に話しかけたときに自動応答が入ってしまいます。

#### 1-5. チャネルアクセストークンを発行

LINE Developers の作成したチャネル → 「Messaging API」タブを下にスクロール → **Channel access token** の「Issue」ボタンをクリック。

表示されたトークンをコピー（後で GitHub Secrets に登録）。これが `LINE_CHANNEL_ACCESS_TOKEN` です。

#### 1-6. 自分のスマホで Bot を友だち追加

同じ「Messaging API」タブの上部に **QR コード** があるので、自分のスマホの LINE で読み取って友だち追加。

#### 1-7. 自分の UserId を取得（一番ハマりやすい部分）

LINE Push API は **「特定ユーザーへ送る」のに UserId が必要** です。これを取得します。

**方法 A: webhook.site を使う（一番簡単）**

1. [https://webhook.site](https://webhook.site) を開く（ブラウザに固有のテスト用 URL が自動生成される）
2. その URL をコピー
3. LINE Developers → 自分のチャネル → 「Messaging API」タブ → **Webhook URL** にその URL を貼って「Update」→ **「Use webhook」を ON**
4. 自分のスマホから Bot に「test」など何か送る
5. webhook.site の画面に JSON イベントが届く。その中の `events[0].source.userId` の値（`U` から始まる長い文字列）をコピー
6. これが `LINE_USER_ID`
7. **取得したら忘れずに**「Use webhook」を OFF に戻す（このスクリプトは webhook を使わないので）

**方法 B: LINE Official Account Manager の管理画面から**

最近のアップデートで、Official Account Manager → 「友だち」一覧から個別ユーザーを開くと UserId が表示される場合があります。表示されない場合は方法 A を使ってください。

---

### 2. GitHub リポジトリの準備

#### 2-1. リポジトリ作成

GitHub で新規リポジトリを作成（**Private 推奨** ── トークンを含む状態ファイルは扱わないが念のため）。

#### 2-2. ファイル配置

このディレクトリの内容をそのままリポジトリのルートに配置：

```
.
├── README.md
├── watch.py
└── .github/
    └── workflows/
        └── watch.yml
```

#### 2-3. Secrets を登録

GitHub リポジトリ → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

以下 2 つを登録：

| Name | Value |
|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | 1-5 で取得したトークン |
| `LINE_USER_ID` | 1-7 で取得した `U` から始まる ID |

#### 2-4. 初回実行（ベースライン作成）

リポジトリの **Actions** タブ → 左側「Heddmann Watch」を選択 → 右側「Run workflow」→ Run。

初回は **必ず通知されません**（ベースラインを作るだけ）。`last_seen.json` がリポジトリに作成されます。

#### 2-5. 動作テスト

- スクリプトの動作を確認したい場合：`last_seen.json` の `latest_date` を手動で過去の日付に書き換えて再度 Run。LINE に通知が来れば成功。

---

## 料金について

- **GitHub Actions**: Public リポジトリは無制限無料。Private でも月 2,000 分の無料枠がある（このスクリプトは 1 回 30 秒程度なので、15 分間隔で月 1,440 分。Private でも余裕で収まる）。
- **LINE Messaging API**: 自分 1 人にしか送らないので、無料枠（コミュニケーションプラン: 月 200 通）で十分。サイト更新は週 1〜2 回ペースなので月 10 通も行きません。

---

## 注意事項とトラブルシューティング

### GitHub Actions の IP がブロックされる可能性

shop-pro.jp が GitHub Actions の IP レンジを bot 扱いして 403 を返してくる可能性があります（ECサイト系では稀にあります）。もしそうなった場合の対応：

1. **Cloudflare Workers Cron** に移植（IP プールが違う、無料枠あり）
2. **自宅 PC + タスクスケジューラ** に移植（家庭用 IP からアクセス）
3. リバースプロキシ系のサービスを噛ます

まずは GitHub Actions で動かしてみて、`watch.py` が 403 を返したら検討してください。

### cron の精度

GitHub Actions のスケジュール実行は、**ピーク時に数分〜数十分遅延** することがあります。シビアな精度が必要なら間隔を短くするか、別の実行環境を検討してください。

### お知らせの構造が変わったら

shop-pro.jp の HTML 構造は何年も変わっていませんが、もし変更があった場合は `extract_latest_notice()` の正規表現を調整してください。Actions のログで `お知らせ欄を解析できませんでした` というエラーが出たらそれが合図です。

### 通知を止めたい / 再開したい

Actions タブ → 「Heddmann Watch」→ 右上「⋯」メニューから「Disable workflow」/「Enable workflow」。

### 通知頻度を変えたい

`.github/workflows/watch.yml` の cron を編集：

- 30 分ごと: `'*/30 * * * *'`
- 5 分ごと: `'*/5 * * * *'`（GitHub の最低間隔は 5 分）
- 営業時間（日本時間 9-22 時）のみ: `'*/15 0-13 * * *'`（UTC 表記)

---

## ファイル説明

| ファイル | 役割 |
|---|---|
| `watch.py` | 監視・通知スクリプト本体 |
| `.github/workflows/watch.yml` | GitHub Actions のスケジュール定義 |
| `last_seen.json` | 自動生成。最後に検知した日付を保存（手で触らない） |
