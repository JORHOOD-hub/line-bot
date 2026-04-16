# 買付証明書 LINE ボット

物件概要書 PDF と購入価格をLINEから送信するだけで、買付証明書PDFが自動生成・返送されるボットです。

## 機能

- 物件概要書 PDF からの自動データ抽出
- 会話形式での情報確認（購入価格、手付金、有効期間）
- Excelテンプレートへの自動記入
- 社印入り買付証明書PDF自動生成
- LINE での簡単操作

## セットアップ手順

### 1. 環境構築（Mac）

```bash
# リポジトリをクローン
cd /Users/ayarino/Downloads/line_bot

# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate

# 依存ライブラリをインストール
pip install -r requirements.txt

# 外部ツールをインストール（Mac）
# Ghostscript
brew install ghostscript

# LibreOffice（Macの場合は .app で提供）
# https://www.libreoffice.org/download/ からダウンロード
# または Homebrew: brew install libreoffice
```

### 2. LINE Messaging API の設定

1. [LINE Developers Console](https://developers.line.biz/en/) にアクセス
2. 新規チャネルを作成（Messaging API）
3. 以下を取得:
   - Channel ID
   - Channel Secret
   - Channel Access Token

4. Webhook URL を設定:
   - `https://your-domain.com/callback`

### 3. 環境変数の設定

```bash
# .env ファイルを作成
cp .env.example .env

# .env を編集し、LINE APIの情報を記入
nano .env
```

**.env の内容:**
```
LINE_CHANNEL_ID=xxxxxxxxxxxx
LINE_CHANNEL_SECRET=xxxxxxxxxxxx
LINE_ACCESS_TOKEN=xxxxxxxxxxxx
FLASK_ENV=production
PORT=5000
LIBREOFFICE_PATH=/Applications/LibreOffice.app/Contents/MacOS/soffice
GHOSTSCRIPT_PATH=/usr/local/bin/gs
```

### 4. Excel テンプレートのコピー

```bash
mkdir -p templates
cp /Users/ayarino/Downloads/買付証明書(自動回復済み).xlsm templates/
```

### 5. ローカル実行テスト

```bash
python main.py

# ログに以下のように表示されればOK
# Running on http://0.0.0.0:5000
```

### 6. Webhook テスト

別ターミナルで:
```bash
# ヘルスチェック
curl http://localhost:5000/health

# テストメッセージ送信
curl -X POST http://localhost:5000/callback \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: test" \
  -d '{"events": []}'
```

## 会話フロー

```
User: 物件概要書PDF送信
Bot: "購入価格を入力してください"

User: "1000万円"
Bot: "手付金は100万円でよろしいですか？"

User: "はい"
Bot: "有効期間を確認します。〇年〇月〇日でよろしいですか？"

User: "確認"
Bot: "買付証明書を生成中..."
Bot: [PDF返送]
```

## デプロイ（Railway / Render）

### Railway での デプロイ

1. [Railway](https://railway.app) にサインアップ
2. 新規プロジェクト → GitHub リポジトリから接続
3. 環境変数を設定（Railway コンソール）
4. 自動デプロイされます

### Render での デプロイ

1. [Render](https://render.com) にサインアップ
2. New Web Service → GitHub リポジトリから接続
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python main.py`
5. 環境変数を設定（Environment タブ）
6. デプロイ開始

## トラブルシューティング

### LibreOffice が見つからない場合

```bash
# インストール確認
which soffice

# Mac での場所
ls /Applications/LibreOffice.app/Contents/MacOS/soffice

# 環境変数で指定
LIBREOFFICE_PATH=/Applications/LibreOffice.app/Contents/MacOS/soffice
```

### Ghostscript が見つからない場合

```bash
# インストール
brew install ghostscript

# 確認
which gs
```

### PDF 生成が失敗する場合

- LibreOffice が起動中でないことを確認
- Ghostscript のバージョン確認：`gs --version`
- ログで詳細なエラーメッセージを確認

## 構成

```
line_bot/
├── main.py                      # Flask メインサーバー
├── handlers/
│   └── message_handler.py       # メッセージ処理
├── logic/
│   ├── conversation_state.py    # ステート管理
│   ├── pdf_extractor.py        # PDF抽出
│   ├── excel_writer.py         # Excel書き込み
│   └── pdf_generator.py        # PDF生成
├── utils/
│   ├── config.py               # 設定
│   └── date_utils.py           # 日付・テキスト解析
├── requirements.txt             # Python依存
├── Dockerfile                   # Docker 設定
└── README.md                    # このファイル
```

## TODO

- [ ] PDF抽出ロジックの詳細仕様確認（Coworkから取得）
- [ ] 複数物件対応
- [ ] エラーハンドリングの強化
- [ ] 単体テストの追加
- [ ] ログ記録の改善
- [ ] 複数言語対応

## ライセンス

MIT License
