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
            # 「管理ID」「ID」などが含まれていれば、その前までを抽出
            if any(kw in name for kw in ['管理ID', 'ID ', '管理']):
                # 「管理ID」の前までを取得
                name = re.sub(r'\s*(?:管理ID|ID|管理).*$', '', name).strip()
            # 「住居」「種別」などが含まれていれば、その前までを抽出（朋竹ハイツ対策）
            if any(kw in name for kw in ['住居 ', '種別 ', '一棟', '（一棟']):
                # 最初の「物件名」だけを取得（空白までを取得するパターン）
                match_name = re.match(r'([^\s]+(?:\s+[^\s]+)*?)(?:\s+(?:住居|種別|一棟|構造|（))', name)
                if match_name:
                    name = match_name.group(1).strip()
            if name and name != '':
                return name

        # パターン2: 最初の行に物件名がある（コルデソル下関対策）
        # 「空室・居住中・賃貸中」などの情報行をスキップして、次の日本語行を物件名と判定
        lines = text.split('\n')
        for i, line in enumerate(lines[:5]):  # 最初の5行をチェック
            line = line.strip()
            # 建物種別情報や記号が含まれない、純粋な日本語行
            if line and not any(kw in line for kw in ['空室', '居住', '賃貸', '【', '【間', '消費税', '価格']):
                # ヒラガナ、カタカナ、漢字を含むかチェック
                if re.search(r'[ぁ-ん]|[ァ-ヴー]|[一-龯]', line):
                    # 数字が多く含まれていない、かつ建物種別や括弧を含まない
                    if not re.search(r'[\d,]{3,}|マンション|ビル|アパート|戸建|（|）|【|】', line):
                        return line

        # パターン3: 建物種別の直前の行にある物件名を検出
        # 「延床面積」「寿マンション」などの流れを想定
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
        # パターン1: 「住居」の直後に住所がある場合（朋竹ハイツ対策）
        # 「住居」と次のラベル（「権」「地目」）の間の住所を抽出
        match = re.search(r'住\s*居\s+(.+?)\s+(?:権|地目|構造|交通)', text)
        if match:
            location = match.group(1).strip()
            if self._is_valid_location(location):
                return location

        # パターン2: 「住居表示」「住所」を優先（これらには都道府県情報が含まれる）
        for label in ['住\s*居\s*表\s*示', '住\s*所']:
            match = re.search(rf'{label}[：:]?\s*(.+?)(?:\n|$)', text)
            if match:
                location = match.group(1).strip()
                # 都道府県や市区町村の文字が含まれているか確認
                if self._is_valid_location(location):
                    return location

        # パターン3: 「所在」「所在地」の後の複数行から住居表示を優先
        # コルデソル下関対策：地番と住居表示が複数行ある場合、住居表示を採用
        for label in ['所\s*在[^\n]*?', '所\s*在\s*地']:
            match = re.search(rf'{label}[：:]?\s*(.+?)(?:地目|権利|交通|建築|〒|$)', text, re.DOTALL)
            if match:
                location_block = match.group(1).strip()
                # 複数行の場合、「(住居表示：」を含む行を探す
                lines = location_block.split('\n')

                # 住居表示を含む行を優先
                for line in lines:
                    if '住居表示' in line or '(' in line:
                        loc = line.strip()
                        if self._is_valid_location(loc):
                            return loc

                # 住居表示がない場合、最後の行（住居表示）を試す
                if lines:
                    loc = lines[-1].strip() if len(lines) > 1 else lines[0].strip()
                    # 最初の「地 」「在地 」を削除
                    loc = re.sub(r'^[地在地]+\s*', '', loc).strip()
                    # 「外観」「画像」などの非地住所情報ではないことを確認
                    if loc and not any(kw in loc for kw in ['外観', '画像', '写真']):
                        if self._is_valid_location(loc):
                            return loc

        return None

    def _is_valid_location(self, location: str) -> bool:
        """所在地として有効か（都道府県や市区町村を含むか）確認"""
        # 都道府県リスト（簡略版）
        prefectures = ['北海道', '青森', '岩手', '宮城', '秋田', '山形', '福島',
                      '茨城', '栃木', '群馬', '埼玉', '千葉', '東京', '神奈川',
                      '新潟', '富山', '石川', '福井', '山梨', '長野', '岐阜',
                      '静岡', '愛知', '三重', '滋賀', '京都', '大阪', '兵庫',
                      '奈良', '和歌山', '鳥取', '島根', '岡山', '広島', '山口',
                      '徳島', '香川', '愛媛', '高知', '福岡', '佐賀', '長崎',
                      '熊本', '大分', '宮崎', '鹿児島', '沖縄']
        return any(pref in location for pref in prefectures)

    def _extract_land_area(self, text: str) -> Optional[float]:
        """土地面積を抽出"""
        patterns = [
            r'土\s*地\s*面\s*積[：:]?\s*([\d.,]+)',
            # 「地積(公簿)」「地積（公簿）」「地積 」のパターン（括弧に対応）
            r'地\s*積\s*(?:[（(][^）)]*[）)]|\([^)]*\))?\s*[：:]?\s*([\d.,]+)',
            # 「公簿」の直後に数値がある（カンマ・ドット対応、改行対応）
            r'公\s*簿\s+[（(]?[^）)]*[）)]?\s*([\d.,]+)',
            r'売\s*却\s*希\s*望\s*面\s*積[：:]?\s*([\d.,]+)',
            # 「面積 283.67㎡」というフォーマット（行の最初の「面積」のみ）
            # 「延床面積」「1階面積」などは除外
            r'(?:^|\n)\s*面\s*積\s+([\d.,]+)\s*㎡'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                try:
                    val_str = match.group(1).replace(',', '')  # カンマを削除
                    return float(val_str)
                except ValueError:
                    pass
        return None

    def _extract_building_area(self, text: str) -> Optional[float]:
        """建物面積を抽出"""
        patterns = [
            r'延\s*床\s*面\s*積\s+([\d.]+)',  # 延床面積（最優先）
            # 「延床 510.93㎡」のように「面積」がない場合
            r'延\s*床\s+(?!面)([\d.]+)',
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
        # パターン1: 「購入価格」「物件価格」「売却価格」などのラベル
        for label in ['購\s*入\s*価格', '物\s*件\s*価格', '売\s*却\s*価格', '価\s*格']:
            match = re.search(rf'{label}[：:]?\s*([\d,]+)\s*万?\s*円?', text)
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

        # パターン1.5: 「価格」ラベルの直前に数値がある場合（改行対応）
        # コルデソル下関対策：「8,200」「価格 万円」という形式
        match = re.search(r'([\d,]+)\s*\n\s*価\s*格\s*万\s*(?:円)?', text)
        if match:
            try:
                price_str = match.group(1).replace(',', '')
                price = int(price_str) * 10000  # 万円なので × 10000
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
