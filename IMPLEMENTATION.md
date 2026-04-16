# 実装概要：買付証明書 LINE ボット

## プロジェクト完成度

### ✅ 完成・実装済み部分（80%）

#### 1. LINE Webhook フレームワーク (`main.py`)
- Flask ベースの Webhook サーバー
- X-Line-Signature 検証
- メッセージイベントのルーティング
- エラーハンドリング
- ヘルスチェックエンドポイント

#### 2. ステート管理 (`logic/conversation_state.py`)
- JSON ファイルベースのユーザー状態管理
- ステートマシン実装
- 物件データの永続化
- タイムスタンプ記録

#### 3. 会話フロー (`handlers/message_handler.py`)
```
待機 → PDF受信待 → 購入価格入力 → 手付金確認 → 有効期間確認 → PDF生成 → 完了
```
- 各ステージでの入力検証
- デフォルト値の自動適用
- 確認メッセージの生成

#### 4. テキスト・日付解析 (`utils/date_utils.py`)
- 価格入力パース（万円、千万円、数値形式）
- 価格フォーマット（金額表示）
- 日付入力パース

#### 5. PDF 抽出ロジック (`logic/pdf_extractor.py`)
- pdfplumber を使用した PDF テキスト抽出
- 物件名、所在地、面積、購入価格の抽出
- 正規表現による柔軟なパターンマッチング

#### 6. Excel テンプレート書き込み (`logic/excel_writer.py`)
- ZIP 操作による XML 直接編集
- openpyxl を使わない社印保持方式
- sharedStrings.xml の更新（物件名・所在地）
- sheet1.xml、sheet2.xml の数値更新
- キャッシュ値（<v>タグ）の同期

#### 7. PDF 生成パイプライン (`logic/pdf_generator.py`)
- LibreOffice 統合（XLSX → PDF）
- Ghostscript 統合（EMF → PNG）
- Pillow/PDF2Image による画像合成
- 社印のオーバーレイ合成

#### 8. 設定管理 (`utils/config.py`)
- 環境変数管理
- ディレクトリ初期化
- デフォルト値（手付金 100万円、有効期間 45日）

#### 9. デプロイメント
- Dockerfile（Python 3.11 + 必要ツール）
- .dockerignore
- 環境変数例（.env.example）
- Railway / Render 対応

### ⚠️ 部分的・要確認部分（15%）

#### 1. PDF 受信・処理
**課題**: LINE から PDF を受信するイベントハンドラーが未実装
```python
# 実装が必要:
@webhook_handler.add(MessageEvent, message=FileMessage)
def handle_file_message(event):
    # ファイルを一時保存
    # PDF抽出器に渡す
    # 結果をユーザー状態に保存
```

#### 2. PDF 返送機能
**課題**: 生成した PDF をLINEで返送する実装が必要
```python
# 実装が必要:
from linebot.models import FileSendMessage

line_bot_api.push_message(
    user_id,
    FileSendMessage(
        original_content_url='...',
        preview_image_url='...'
    )
)
```

#### 3. Cowork との統合
**課題**: 既完成の PDF 抽出・Excel 書き込みコードの場所が未確認
- Cowork セッション内のコードを特定する必要がある
- 可能な場合は、そのコードを統合する

### ❌ 未実装部分（5%）

1. **単体テスト**
   - unittest / pytest による包括的なテストスイート

2. **ログ記録**
   - logging モジュール統合
   - 本番環境でのログ集約

3. **複数物件対応**
   - スケーラビリティ向上

4. **複数言語対応**

## 次のステップ

### 優先度高：実装必須

1. **PDF ファイル受信ハンドラーの実装**
   ```python
   # main.py に追加
   from linebot.models import FileMessage
   
   @webhook_handler.add(MessageEvent, message=FileMessage)
   def handle_pdf(event):
       # ファイルID から PDF をダウンロード
       message_content = line_bot_api.get_message_content(event.message.id)
       # 一時ファイルに保存
       # PDFExtractor で処理
       # 物件データをユーザー状態に保存
   ```

2. **PDF 返送機能の実装**
   - 生成した PDF の LINE アップロード
   - FileSendMessage の実装

3. **Cowork コード統合**
   - 既完成のロジックを統合
   - テスト

### 優先度中：動作確認

1. **ローカル環境での動作テスト**
   - `python main.py` で起動
   - LINE Bot Tester で メッセージ送信

2. **外部ツール動作確認**
   - LibreOffice CLI 実行確認
   - Ghostscript 実行確認

3. **PDF 生成パイプラインのテスト**
   - サンプル XLSX で PDF 生成
   - 社印オーバーレイ確認

### 優先度低：改善

1. エラーハンドリング強化
2. ログ記録体系
3. レート制限
4. ユーザー入力検証

## コード構造

```
main.py（メインサーバー）
├─ handlers/message_handler.py（メッセージ処理）
│   └─ 各ステート処理関数
├─ logic/
│   ├─ conversation_state.py（ステート管理）
│   ├─ pdf_extractor.py（PDF抽出）
│   ├─ excel_writer.py（Excel書き込み）
│   └─ pdf_generator.py（PDF生成）
└─ utils/
    ├─ config.py（設定）
    └─ date_utils.py（日付・テキスト解析）
```

## 外部依存

### Python ライブラリ
- `line-bot-sdk`: LINE Messaging API
- `openpyxl`: Excel 操作（参照のみ）
- `pdfplumber`: PDF テキスト抽出
- `pillow`: 画像操作
- `pdf2image`: PDF → 画像変換
- `pypdf`: PDF 合成

### 外部ツール
- `LibreOffice`: XLSX → PDF 変換（ヘッドレスモード）
- `Ghostscript`: EMF → PNG 変換（社印）

## トラブルシューティング

### 状態管理が反映されない
- `data/user_states.json` が存在することを確認
- ファイルのパーミッション確認

### PDF 生成に失敗
- LibreOffice がバックグラウンドで起動中でないことを確認
- `/tmp` に書き込み権限があることを確認
- Ghostscript のバージョン確認：`gs --version`

### LINE との連携がされない
- `LINE_CHANNEL_SECRET` の署名検証確認
- Webhook URL が正しく設定されているか確認
- ネットワーク接続確認

## 開発時の Tips

### ローカルテスト
```bash
# 仮想環境起動
source venv/bin/activate

# 基本テスト実行
python test_basic.py

# サーバー起動
python main.py
```

### LINE デバッグ
```bash
# LINE Tester
# https://line.biz/en/news/service/development-tools/line-tester/

# または curl でテスト
curl -X POST http://localhost:5000/callback \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: <signature>" \
  -d '{"events": [...]}' 
```

### ファイル操作デバッグ
```python
# utils/config.py で Path を確認
print(config.BASE_DIR)
print(config.STATE_FILE_PATH)
print(config.OUTPUT_DIR)
```
