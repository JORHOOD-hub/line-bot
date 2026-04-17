import pdfplumber
import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

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
                logger.info(f"DEBUG: Extracted text length: {len(text)} characters")
                logger.info(f"DEBUG: First 500 chars: {text[:500]}")

                # 物件名、所在地などを抽出
                extracted_data['property_name'] = self._extract_property_name(text)
                extracted_data['location'] = self._extract_location(text)
                extracted_data['land_area'] = self._extract_land_area(text)
                extracted_data['building_area'] = self._extract_building_area(text)
                extracted_data['purchase_price'] = self._extract_purchase_price(text)

                # 抽出結果をログ出力
                logger.info(f"EXTRACTION RESULT: {extracted_data}")

        except Exception as e:
            logger.error(f"Error extracting PDF: {e}", exc_info=True)

        return extracted_data

    def _extract_property_name(self, text: str) -> Optional[str]:
        """物件名を抽出"""
        # パターン1: 「物件名：」「物件名 」の後の文字列
        match = re.search(r'物\s*件\s*名[：:]?\s*([^\n]+)', text)
        if match:
            name = match.group(1).strip()
            if name and name != '':
                return name

        # パターン2: 建物種別の直前の行にある物件名を検出
        # 「延床面積」「寿マンション」などの流れを想定
        lines = text.split('\n')
        for i, line in enumerate(lines):
            # 「マンション」「ビル」などが含まれる行
            if any(kw in line for kw in ['マンション', 'ビル', 'アパート', '戸建', '住宅']):
                # 建物種別の行（「中古（1棟）マンション」など）ではない
                if not re.search(r'中古|新築|築', line):
                    name = line.strip()
                    if name and 1 < len(name) < 50 and not any(c.isdigit() for c in name[:3]):
                        return name

        return None

    def _extract_location(self, text: str) -> Optional[str]:
        """所在地を抽出"""
        # 「所在地」の後の文字列を抽出（スペースに対応）
        match = re.search(r'所\s*在\s*地[：:]?\s*(.+?)(?:\n|$)', text)
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
            r'土\s*地\s*面\s*積[：:]?\s*([\d.]+)',
            r'地\s*積[：:]?\s*([\d.]+)',
            r'売\s*却\s*希\s*望\s*面\s*積[：:]?\s*([\d.]+)',
            # 「面積 283.67㎡」というフォーマット（行の最初の「面積」のみ）
            # 「延床面積」「1階面積」などは除外
            r'(?:^|\n)\s*面\s*積\s+([\d.]+)\s*㎡'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
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
        # パターン1: 「購入価格 3,800万円」
        match = re.search(r'購\s*入\s*価格[：:]?\s*([\d,]+)\s*万?\s*円', text)
        if match:
            try:
                price_str = match.group(1).replace(',', '')
                price = int(price_str)
                # もし万円単位なら × 10000
                if '万' in text[match.start():match.end()]:
                    price *= 10000
                return price
            except ValueError:
                pass

        # パターン2: 「価 格」の直前の数値を探す（改行対応）
        # 「3,800万円\n価 格」というフォーマット
        match = re.search(r'([\d,]+)\s*万\s*円\s*(?:\n|\s)*価\s*格', text)
        if match:
            try:
                price_str = match.group(1).replace(',', '')
                price = int(price_str) * 10000  # 万円なので × 10000
                return price
            except ValueError:
                pass

        # パターン3: 単純に「(数値)万円」を探す（フォーマット「価 格」「3,800万円」が別の場合）
        match = re.search(r'([\d,]+)\s*万\s*円', text)
        if match:
            try:
                price_str = match.group(1).replace(',', '')
                price = int(price_str) * 10000  # 万円なので × 10000
                logger.info(f"Found purchase price via pattern 3: {price}")
                return price
            except ValueError:
                pass

        return None
