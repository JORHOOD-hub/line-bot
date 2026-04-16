#!/usr/bin/env python3
"""修正機能のテスト"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from logic.conversation_state import state_manager
from handlers.修正_handler import handle_修正指示
from handlers.message_handler import generate_certificate_pdf
from datetime import datetime, timedelta

def test_修正機能():
    """修正機能のテスト"""
    user_id = "test_修正_001"

    # ユーザーの初期状態を作成
    user_state = state_manager.get_state(user_id)
    user_state.state = 'completed'
    user_state.property_data = {
        'property_name': 'プレアール高松西町',
        'location': '香川県高松市西町27-9',
        'land_area': 329.8,
        'building_area': 389.88,
        'purchase_price': 10000000,
        'down_payment': 1000000,
        'created_date': datetime.now().isoformat(),
        'expiration_date': (datetime.now() + timedelta(days=45)).isoformat(),
    }
    state_manager.set_state(user_state)

    # 初期PDFを生成
    print("=== 初期PDF生成 ===")
    pdf_path = generate_certificate_pdf(user_id)
    print(f"✓ 初期PDF: {pdf_path}")

    # 修正指示テスト1: 手付金を変更
    print("\n=== 修正テスト1: 手付金を50万円に変更 ===")
    response, modified_pdf = handle_修正指示(user_id, "手付金は50万円で")
    print(response)
    if modified_pdf:
        print(f"✓ 修正PDF: {modified_pdf}")

    # 修正指示テスト2: 備考を追加
    print("\n=== 修正テスト2: 備考に文章を追加 ===")
    response, modified_pdf = handle_修正指示(user_id, "備考に「このマンションは新築で、駅近です。」")
    print(response)
    if modified_pdf:
        print(f"✓ 修正PDF: {modified_pdf}")

    # 修正指示テスト3: 有効期限を変更
    print("\n=== 修正テスト3: 有効期限を2026年6月30日に ===")
    response, modified_pdf = handle_修正指示(user_id, "有効期限を2026年6月30日に変更")
    print(response)
    if modified_pdf:
        print(f"✓ 修正PDF: {modified_pdf}")

    print("\n=== テスト完了 ===")

if __name__ == '__main__':
    test_修正機能()
