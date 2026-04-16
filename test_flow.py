#!/usr/bin/env python3
"""
買付証明書ボットの エンドツーエンドテスト
実際のLINEなしで、ローカルでテストする
"""

import sys
from pathlib import Path
import tempfile

# プロジェクトパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from logic.conversation_state import state_manager
from logic.pdf_extractor import PDFExtractor
from logic.excel_writer import ExcelWriter
from logic.pdf_generator import PDFGenerator
from handlers.message_handler import handle_message, generate_certificate_pdf
from utils.date_utils import parse_price_input
from utils.config import config
from datetime import datetime, timedelta


def test_scenario():
    """
    実際のLINE会話フローをシミュレート
    """
    print("\n" + "=" * 70)
    print("🤖 買付証明書ボット エンドツーエンドテスト")
    print("=" * 70)

    user_id = "test_user_001"
    config.init_directories()

    # Step 1: PDFファイルを取得（テスト用）
    print("\n【Step 1】物件概要書PDFを送信")
    print("-" * 70)

    # テスト用PDFファイル（Excelから出力したもの）
    test_pdf = Path("/Users/ayarino/Downloads/香川/プレアール高松西町概要書＿のコピー.pdf")

    if not test_pdf.exists():
        print(f"❌ テストPDFが見つかりません: {test_pdf}")
        print("   別のPDFパスを指定してください")
        return

    print(f"✓ PDF: {test_pdf.name}")

    # PDF から物件情報を抽出
    print("\n  【PDF抽出中】")
    extractor = PDFExtractor(str(test_pdf))
    extracted_data = extractor.extract_data()

    print(f"  物件名: {extracted_data.get('property_name', 'N/A')}")
    print(f"  所在地: {extracted_data.get('location', 'N/A')}")
    print(f"  土地面積: {extracted_data.get('land_area', 'N/A')} ㎡")
    print(f"  建物面積: {extracted_data.get('building_area', 'N/A')} ㎡")
    print(f"  購入価格: {extracted_data.get('purchase_price', 'N/A')} 円")

    # ユーザー状態を保存
    for key, value in extracted_data.items():
        if value is not None:
            state_manager.update_property_data(user_id, key, value)

    user_state = state_manager.get_state(user_id)
    user_state.state = 'waiting_price'
    state_manager.set_state(user_state)

    # Step 2: 購入価格を入力
    print("\n【Step 2】購入価格を入力")
    print("-" * 70)

    price_input = "1000万円"
    print(f"ユーザー入力: {price_input}")

    price = parse_price_input(price_input)
    print(f"✓ 解析結果: {price:,} 円")

    state_manager.update_property_data(user_id, 'purchase_price', price)
    user_state = state_manager.get_state(user_id)
    user_state.state = 'waiting_down_payment'
    state_manager.set_state(user_state)

    # Step 3: 手付金確認
    print("\n【Step 3】手付金を確認")
    print("-" * 70)

    down_payment_input = "はい"
    print(f"ユーザー入力: {down_payment_input}")

    down_payment = 1000000  # デフォルト100万
    print(f"✓ 手付金: {down_payment:,} 円（デフォルト）")

    state_manager.update_property_data(user_id, 'down_payment', down_payment)

    # 有効期間を計算
    created_date = datetime.now()
    expiration_date = created_date + timedelta(days=45)

    state_manager.update_property_data(user_id, 'created_date', created_date.isoformat())
    state_manager.update_property_data(user_id, 'expiration_date', expiration_date.isoformat())

    user_state = state_manager.get_state(user_id)
    user_state.state = 'waiting_expiration'
    state_manager.set_state(user_state)

    print(f"✓ 有効期間: {expiration_date.strftime('%Y年%m月%d日')}")

    # Step 4: 有効期間確認
    print("\n【Step 4】有効期間を確認")
    print("-" * 70)

    expiration_input = "確認"
    print(f"ユーザー入力: {expiration_input}")
    print(f"✓ 確定")

    # Step 5: PDF生成
    print("\n【Step 5】買付証明書PDFを生成")
    print("-" * 70)

    user_state = state_manager.get_state(user_id)
    user_state.state = 'generating'
    state_manager.set_state(user_state)

    pdf_path = generate_certificate_pdf(user_id)

    if pdf_path and Path(pdf_path).exists():
        print(f"✓ PDF生成成功")
        print(f"  ファイル: {Path(pdf_path).name}")
        print(f"  サイズ: {Path(pdf_path).stat().st_size / 1024:.1f} KB")
    else:
        print(f"❌ PDF生成失敗")
        return

    # Step 6: 結果確認
    print("\n【Step 6】結果確認")
    print("-" * 70)

    user_state = state_manager.get_state(user_id)
    print(f"最終状態: {user_state.state}")
    print(f"保存データ:")
    for key, value in user_state.property_data.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("✅ テスト完了")
    print("=" * 70)
    print(f"\n生成されたPDF: {pdf_path}")
    print("\n次のステップ:")
    print("  1. PDFを開いて社印の位置・サイズを確認")
    print("  2. 精度が高ければ本番LINE連携へ")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    test_scenario()
