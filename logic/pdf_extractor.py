import pdfplumber
import re
from typing import Dict, Optional

class PDFExtractor:
    """物件概要書 PDF から物件情報を抽出"""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract_data(self) -> Dict[str, any]:
        """
        PDFから物件情報を抽出
        返り値: {
            'property_name': '...',
            'location': '...',
            'land_area': 248.01,
            'building_area': 520.22,
            'purchase_price': 56800000,
            ...
        }
        """
        extracted_data = {
            'property_name': None,
            'location': None,
            'land_area': None,
            'building_area': None,
            'purchase_price': None,
        }

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # 全ページからテキスト抽出
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""

                # デバッグ：抽出されたテキストをログ出力
                print(f"DEBUG: Extracted text length: {len(text)} characters")
                print(f"DEBUG: First 500 chars: {text[:500]}")

                # 物件名、所在地などを抽出
                extracted_data['property_name'] = self._extract_property_name(text)
                extracted_data['location'] = self._extract_location(text)
                extracted_data['land_area'] = self._extract_land_area(text)
                extracted_data['building_area'] = self._extract_building_area(text)
                extracted_data['purchase_price'] = self._extract_purchase_price(text)

        except Exception as e:
            print(f"Error extracting PDF: {e}")

        return extracted_data

    def _extract_property_name(self, text: str) -> Optional[str]:
        """物件名を抽出"""
        # パターン1: 「物件名：」「物件名 」の後の文字列
        match = re.search(r'物件名[：:]?\s*([^\n]+)', text)
        if match:
            name = match.group(1).strip()
            if name and name != '':
                return name

        # パターン2: 「マンション」「ビル」「アパート」などのキーワードを含む単語を検出
        # 「延床面積」の直前の行にある可能性が高い
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if any(kw in line for kw in ['マンション', 'ビル', 'アパート', '戸建', '住宅', '建物']):
                name = line.strip()
                if name and 1 < len(name) < 50:
                    return name

        return None

    def _extract_location(self, text: str) -> Optional[str]:
        """所在地を抽出"""
        # 「所在地」の後の文字列を抽出
        match = re.search(r'所在地[：:]?\s*(.+?)(?:\n|$)', text)
        if match:
            location = match.group(1).strip()
            # 最初の「地 」「在地 」を削除
            location = re.sub(r'^[地在地]+\s*', '', location).strip()
            if location:
                return location
        return None

    def _extract_land_area(self, text: str) -> Optional[float]:
        """土地面積を抽出"""
        patterns = [
            r'土地面積[：:]?\s*([\d.]+)',
            r'地積[：:]?\s*([\d.]+)',
            r'売却希望面積[：:]?\s*([\d.]+)',
            # 「面積 283.67㎡」というフォーマット（「1階面積」「2階面積」は除外）
            r'(?<!階)\s*面積\s+([\d.]+)\s*㎡'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        return None

    def _extract_building_area(self, text: str) -> Optional[float]:
        """建物面積を抽出"""
        patterns = [
            r'延\s*床\s*面\s*積\s+([\d.]+)',  # 延床面積（最優先）
            r'建\s*物\s*面\s*積\s*([\d.]+)',
            r'床\s*面\s*積\s*([\d.]+)',
            r'合\s*計\s*([\d.]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        return None

    def _extract_purchase_price(self, text: str) -> Optional[int]:
        """購入価格を抽出"""
        # 「購入価格」「購 入 価格」の後の数値を抽出
        match = re.search(r'購\s*入\s*価格[：:]?\s*([\d,]+)\s*(?:円|万円)', text)
        if match:
            try:
                price_str = match.group(1).replace(',', '')
                return int(price_str)
            except ValueError:
                pass
        return None
