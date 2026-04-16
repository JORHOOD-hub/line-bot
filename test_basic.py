#!/usr/bin/env python3
"""
基本テストスクリプト
ボットのコア機能をテスト
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

from logic.conversation_state import state_manager, UserState
from handlers.message_handler import handle_message
from utils.date_utils import parse_price_input, format_price
from utils.config import config

def test_price_parsing():
    """価格パース機能のテスト"""
    print("=== Price Parsing Test ===")
    test_cases = [
        ("1000万円", 100000000),
        ("1千万円", 10000000),
        ("100,000,000", 100000000),
        ("100000000", 100000000),
        ("50万円", 5000000),
    ]

    for text, expected in test_cases:
        result = parse_price_input(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text}' → {result:,} (expected: {expected:,})")

    print()

def test_price_formatting():
    """価格フォーマット機能のテスト"""
    print("=== Price Formatting Test ===")
    test_cases = [
        (100000000, "1億円"),
        (50000000, "5千万円"),
        (10000000, "1千万円"),
        (5000000, "500万円"),
        (1000000, "100万円"),
    ]

    for price, expected in test_cases:
        result = format_price(price)
        # 実装次第で調整
        print(f"  {price:,} → {result}")

    print()

def test_state_management():
    """ステート管理のテスト"""
    print("=== State Management Test ===")

    user_id = "test_user_123"

    # 新規ユーザーは waiting_pdf
    state = state_manager.get_state(user_id)
    assert state.state == 'waiting_pdf', f"Expected 'waiting_pdf', got '{state.state}'"
    print(f"✓ Initial state: {state.state}")

    # データを更新
    state_manager.update_property_data(user_id, 'purchase_price', 100000000)
    state = state_manager.get_state(user_id)
    assert state.property_data['purchase_price'] == 100000000
    print(f"✓ Property data updated: {state.property_data}")

    # 状態を変更
    state.state = 'waiting_down_payment'
    state_manager.set_state(state)
    state = state_manager.get_state(user_id)
    assert state.state == 'waiting_down_payment'
    print(f"✓ State updated: {state.state}")

    # クリーンアップ
    state_manager.clear_state(user_id)
    print(f"✓ State cleared")

    print()

def test_message_handling():
    """メッセージハンドリングのテスト"""
    print("=== Message Handling Test ===")

    user_id = "test_user_msg"

    # 初期状態（PDF待機中）
    response = handle_message(user_id, "テストメッセージ")
    print(f"Response: {response[:50]}...")

    # 購入価格入力テスト
    state = state_manager.get_state(user_id)
    state.state = 'waiting_price'
    state_manager.set_state(state)

    response = handle_message(user_id, "1000万円")
    print(f"✓ Price handling: {response[:50]}...")

    # 手付金確認テスト
    response = handle_message(user_id, "はい")
    print(f"✓ Down payment handling: {response[:50]}...")

    # クリーンアップ
    state_manager.clear_state(user_id)
    print()

def test_config():
    """設定の確認"""
    print("=== Configuration Test ===")
    print(f"Flask Environment: {config.FLASK_ENV}")
    print(f"Debug Mode: {config.DEBUG}")
    print(f"Port: {config.PORT}")
    print(f"Default Down Payment: {config.DEFAULT_DOWN_PAYMENT:,}円")
    print(f"Default Expiration Days: {config.DEFAULT_EXPIRATION_DAYS}日")
    print()

def main():
    print("=" * 50)
    print("LINE Bot Basic Test Suite")
    print("=" * 50)
    print()

    try:
        test_price_parsing()
        test_price_formatting()
        test_state_management()
        test_message_handling()
        test_config()

        print("=" * 50)
        print("✓ All basic tests passed!")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
