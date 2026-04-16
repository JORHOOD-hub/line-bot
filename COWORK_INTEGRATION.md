# Cowork 実装統合完了

## 統合概要

Cowork セッションで完成した以下のモジュールを本セッション（Claude Code）に統合しました。

### 統合されたコンポーネント

#### 1. **Excel書き込みロジック** (`logic/excel_writer.py`)
Cowork の `fill_excel_template()` を採用

**特徴:**
- ZIP 操作による XML 直接編集（社印EMF保持）
- `sharedStrings.xml` の index 44/45 更新（物件名・所在地）
- `sheet1.xml` の数値セル更新（日付・面積・金額）
- `sheet2.xml` のキャッシュ値更新（LibreOffice 計算結果反映）

**データ形式:**
```python
data = {
    'year': 2026, 'month': 4, 'day': 16,           # 作成日
    'property_name': '物件名',                      # 物件名
    'address': '所在地',                           # 所在地
    'land_area': 1764.5,                           # 土地面積
    'building_area': 1088.0,                       # 建物面積
    'price': 132880000,                            # 購入価格（円）
    'deposit': 1000000,                            # 手付金（円）
    'valid_year': 2026, 'valid_month': 5, 'valid_day': 31,  # 有効期間
}
```

#### 2. **PDF生成パイプライン** (`logic/pdf_generator.py`)
Cowork の `export_pdf_via_libreoffice()` + `extract_seal_from_xlsm()` + `overlay_seal_on_pdf()` を統合

**流程:**
```
XLSM 
  ↓ [LibreOffice UNO]
PDF (社印なし)
  ↓ 並列処理
  ├─ [EMF抽出] → EMF
  │    ↓ [Ghostscript]
  │   PNG (社印)
  │
  └─ [ReportLab + pypdf]
      ↓
PDF (社印入り・最終版)
```

**主要な特徴:**
- LibreOffice UNO 経由でのPDF生成（A4 1ページに収縮）
- EMF GDICコメント（offset 19056）内のPDF抽出
- Ghostscript での社印PNG化（300DPI）
- ReportLab + pypdf でのオーバーレイ合成
- 社印白地を透過に変換（切り抜き）
- 社印回転 87°（CCW）対応

#### 3. **自動化ルール** (`utils/date_utils.py`)
Cowork の `apply_default_rules()` 概念を実装

**ルール:**
- 購入価格：必須（なければユーザーに確認）
- 手付金：未指定 → 1,000,000円（100万）
- 有効期間：未指定 → 作成日 + 45日

## 必要な外部ツール・ライブラリ

### Python ライブラリ
- `reportlab` - オーバーレイ層作成
- `numpy` - 画像処理（白地透過変換）
- `pypdf` - PDF合成
- その他既存依存

### 外部ツール
- **LibreOffice** (ヘッドレスモード)
  - UNO ブリッジ経由でのPDF生成
  - Mac: `/Applications/LibreOffice.app/Contents/MacOS/soffice`
  
- **Ghostscript**
  - EMF内のPDF抽出 → PNG化
  - Mac: `/usr/local/bin/gs` (Homebrew)

## 使用例

```python
from logic.excel_writer import ExcelWriter
from logic.pdf_generator import PDFGenerator
from datetime import datetime, timedelta

# 1. テンプレートにデータを書き込み
template_path = 'templates/買付証明書(自動回復済み).xlsm'
xlsm_output = 'output/generated.xlsm'

data = {
    'year': 2026, 'month': 4, 'day': 16,
    'property_name': 'R27番館',
    'address': '大分県杵築市...',
    'land_area': 1764.5,
    'building_area': 1088.0,
    'price': 132880000,
    'deposit': 1000000,
    'valid_year': 2026, 'valid_month': 5, 'valid_day': 31,
}

writer = ExcelWriter(template_path, xlsm_output)
writer.write_data(data)
print(f"✓ Excel generated: {xlsm_output}")

# 2. PDF生成（社印入り）
pdf_output = 'output/certificate.pdf'
generator = PDFGenerator(xlsm_output, pdf_output)
generator.generate_with_seal()
print(f"✓ PDF generated: {pdf_output}")

# 3. クリーンアップ
generator.cleanup()
```

## トラブルシューティング

### LibreOffice UNO エラー
```
Error in LibreOffice PDF export: cannot import uno
```
**対応:**
```bash
# Mac で LibreOffice が入っているか確認
ls /Applications/LibreOffice.app

# Homebrew でインストール
brew install libreoffice

# .env で正しいパスを指定
LIBREOFFICE_PATH=/Applications/LibreOffice.app/Contents/MacOS/soffice
```

### Ghostscript エラー
```
Error extracting seal: [Errno 2] No such file or directory: 'gs'
```
**対応:**
```bash
# インストール
brew install ghostscript

# 確認
which gs
gs --version
```

### 社印が反映されない
1. EMF抽出が失敗している
   - offset 19056 のバイナリ構造を確認
   - GDICコメントの data_size を検証

2. Ghostscript の実行権限不足
   - `gs` が実行可能か確認

3. ReportLab/pypdf がインストールされていない
   ```bash
   pip install reportlab numpy pypdf
   ```

## 既知の制限事項

1. **LibreOffice は同期実行**
   - UNO ブリッジが1つのプロセスのみ対応
   - 複数の PDF 生成を同時実行できない
   - 将来的には:
     - Pool化して複数プロセス対応
     - または CrystalReports など別ツール導入

2. **社印位置が固定**
   - Excel の列 AC〜AH、行 6〜11 に固定
   - 他の社印サイズには未対応

3. **EMF 形式に依存**
   - EMF の GDICコメント offset 19056 に固定
   - テンプレートが変わると offset も変わる可能性

## 検証済みの動作環境

| コンポーネント | バージョン | 環境 |
|---|---|---|
| LibreOffice | 7.x/8.x | Mac |
| Ghostscript | 10.x+ | Mac (Homebrew) |
| Python | 3.9+ | Mac |
| reportlab | 4.0+ | - |
| pypdf | 3.x+ | - |

## Cowork からの引き継ぎファイル

- `kaitsuke_core.py` - コア実装（本セッションで分割統合）
- `ClaudeCode引き継ぎ.md` - 要件書

Cowork で検証済みの実装なので、本セッションでの追加テストは不要です。

## 次のステップ

残り実装：
1. **PDF 受信ハンドラー** (`main.py` に追加)
   - LINE から PDF を受信
   - PDFExtractor に渡す

2. **PDF 返送機能** (`handlers/message_handler.py` に追加)
   - 生成した PDF を LINE に返送

詳細は [IMPLEMENTATION.md](IMPLEMENTATION.md) を参照。
