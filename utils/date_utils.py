import re
from typing import Optional

def parse_price_input(text: str) -> Optional[int]:
    """
    テキスト入力から購入価格を抽出
    対応形式：
    - 1億円、1.2億、1.2億円
    - 1000万円、3500万、15000万円
    - 2千万円、1千万
    - 100,000,000
    - 100000000
    """
    text = text.strip()

    # 億円 形式: "1億円" "1.2億" → 100000000, 120000000
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*億(?:円)?', text)
    if match:
        try:
            amount = float(match.group(1).replace(',', ''))
            return int(amount * 100000000)
        except ValueError:
            pass

    # 千万 形式（優先度高）: "2千万円" "1千万" → 20000000, 10000000
    match = re.search(r'(\d+)\s*千\s*万\s*(?:円)?', text)
    if match:
        try:
            amount = int(match.group(1))
            return amount * 10000000
        except ValueError:
            pass

    # 万 形式: "1000万円" "3500万" "15000万円" → 10000000, 35000000, 150000000
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*万\s*(?:円)?', text)
    if match:
        try:
            amount = float(match.group(1).replace(',', ''))
            return int(amount * 10000)
        except ValueError:
            pass

    # 数値形式（カンマ区切り）: "100,000,000"
    match = re.search(r'^(\d+(?:,\d{3})*)\s*(?:円)?$', text)
    if match:
        try:
            amount = match.group(1).replace(',', '')
            return int(amount)
        except ValueError:
            pass

    # 数値形式（そのまま）: "100000000"
    match = re.search(r'^(\d+)\s*(?:円)?$', text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    return None


def format_price(price: int) -> str:
    """
    金額をフォーマット
    100000000 → "1億円" or "100,000,000円"
    """
    if price >= 100000000:
        # 億円で表示
        oku = price // 100000000
        remainder = (price % 100000000) // 10000
        if remainder == 0:
            return f"{oku}億円"
        else:
            return f"{oku}億{remainder}万円"
    elif price >= 10000:
        # 万円で表示
        man = price // 10000
        return f"{man}万円"
    else:
        return f"{price:,}円"


def validate_date_input(text: str) -> Optional[tuple]:
    """
    日付入力をパース（YYYY年MM月DD日など）
    返り値: (year, month, day) or None
    """
    # 年月日形式のパターン
    match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
    if match:
        try:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            # 簡易検証
            if 1 <= month <= 12 and 1 <= day <= 31:
                return (year, month, day)
        except ValueError:
            pass

    return None
