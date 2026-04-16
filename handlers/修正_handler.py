"""
PDF修正ハンドラー
ユーザーのメッセージから修正内容を抽出して、PDFを再生成
"""

import re
from typing import Tuple, Optional
from logic.conversation_state import state_manager
from utils.date_utils import parse_price_input


def handle_修正指示(user_id: str, message: str) -> Tuple[str, Optional[str]]:
    """
    ユーザーの修正指示を処理
    例：「手付金は50万円で」「備考に〇〇を追加」

    返り値: (応答メッセージ, PDF パス or None)
    """
    user_state = state_manager.get_state(user_id)

    if not hasattr(user_state, 'property_data') or user_state.property_data is None:
        return "申し訳ございません。まず物件情報を入力してください。", None

    修正項目 = []

    # 手付金の修正
    if any(kw in message for kw in ['手付金', 'てつけきん', '頭金']):
        amount = parse_price_input(message)
        if amount is not None:
            state_manager.update_property_data(user_id, 'down_payment', amount)
            修正項目.append(f"手付金：{amount:,}円")

    # 購入価格の修正
    if any(kw in message for kw in ['購入価格', 'こうにゅうかかく', '価格']):
        amount = parse_price_input(message)
        if amount is not None:
            state_manager.update_property_data(user_id, 'purchase_price', amount)
            修正項目.append(f"購入価格：{amount:,}円")

    # 物件名の修正
    if any(kw in message for kw in ['物件名を', '物件名は', '物件を']):
        # 「物件名を〇〇に」「物件名は〇〇」というパターンを抽出
        match = re.search(r'物件名[を|は](.+?)(?:に$|で$|。|$)', message)
        if match:
            property_name = match.group(1).strip()
            state_manager.update_property_data(user_id, 'property_name', property_name)
            修正項目.append(f"物件名：{property_name}")

    # 所在地の修正
    if any(kw in message for kw in ['所在地を', '所在地は', '住所を', '住所は']):
        match = re.search(r'(?:所在地|住所)[を|は](.+?)(?:に$|で$|。|$)', message)
        if match:
            location = match.group(1).strip()
            state_manager.update_property_data(user_id, 'location', location)
            修正項目.append(f"所在地：{location}")

    # 有効期限の修正
    if any(kw in message for kw in ['有効期限', '期限']):
        # 「2026年5月31日」というパターンを抽出
        match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', message)
        if match:
            year, month, day = match.groups()
            from datetime import datetime
            exp_date = datetime(int(year), int(month), int(day))
            state_manager.update_property_data(user_id, 'expiration_date', exp_date.isoformat())
            修正項目.append(f"有効期限：{year}年{month}月{day}日")

    # 備考の修正・追加
    if '備考' in message:
        # 「備考に」の後の内容を抽出
        match = re.search(r'備考に[「『]?(.+?)[」』]?(?:を|$)', message)
        if match:
            remarks = match.group(1).strip()
            # 既存の備考があれば改行で追加、なければ新規追加
            existing_remarks = user_state.property_data.get('remarks', '')
            if existing_remarks:
                new_remarks = existing_remarks + '\n' + remarks
            else:
                new_remarks = remarks
            state_manager.update_property_data(user_id, 'remarks', new_remarks)
            修正項目.append(f"備考を追加")

    # 修正がない場合
    if not 修正項目:
        return "申し訳ございません。修正内容が認識できませんでした。\n例：「手付金は50万円で」「有効期限を2026年6月30日に」", None

    # 修正内容を確認して、PDFを再生成
    try:
        # 遅延インポート（循環参照を回避）
        from handlers.message_handler import generate_certificate_pdf

        user_state.state = 'generating'
        state_manager.set_state(user_state)

        pdf_path = generate_certificate_pdf(user_id)

        if pdf_path:
            response = "修正しました！\n\n修正内容：\n" + "\n".join(f"✓ {item}" for item in 修正項目)
            return response, pdf_path
        else:
            return "申し訳ございません。PDF生成に失敗しました。", None

    except Exception as e:
        return f"申し訳ございません。エラーが発生しました。\n{str(e)}", None
