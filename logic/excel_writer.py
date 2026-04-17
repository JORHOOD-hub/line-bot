import zipfile
import re
import shutil
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ExcelWriter:
    """Excelテンプレートに値を書き込み（ZIP操作方式・Cowork実装統合）

    重要: openpyxlでxlsmを読み込むとEMF画像（社印）が消える。
    必ずZIP操作でXMLを直接編集すること。
    """

    def __init__(self, template_path: str, output_path: str):
        self.template_path = Path(template_path)
        self.output_path = Path(output_path)

    def write_data(self, data: Dict[str, Any]) -> bool:
        """
        テンプレートにデータを書き込み（ZIP操作方式）

        data: {
            'year': 2026, 'month': 4, 'day': 16,         # 作成日
            'property_name': 'R27番館',                  # 物件名
            'address': '大分県杵築市...',                 # 所在地
            'land_area': 1764.5,                         # 土地面積(㎡)
            'building_area': 1088.0,                     # 建物面積(㎡)
            'price': 132880000,                          # 購入価格(円)
            'deposit': 1000000,                          # 手付金(円)
            'valid_year': 2026, 'valid_month': 5, 'valid_day': 31,  # 有効期間
        }
        """
        logger.info(f"DEBUG write_data received data: {data}")
        try:
            shutil.copy(self.template_path, self.output_path)

            # ZIP形式で開いて、各XMLを編集
            with zipfile.ZipFile(self.output_path, 'r') as zin:
                files = {name: zin.read(name) for name in zin.namelist()}

            # --- sharedStrings.xml の更新（物件名・所在地）---
            ss = files['xl/sharedStrings.xml'].decode('utf-8')
            ss = self._update_shared_string(ss, 44, data.get('property_name', ''))
            ss = self._update_shared_string(ss, 45, data.get('address', ''))
            files['xl/sharedStrings.xml'] = ss.encode('utf-8')

            # --- sheet1.xml の更新（入力用シート）---
            s1 = files['xl/worksheets/sheet1.xml'].decode('utf-8')
            # 作成日
            s1 = self._set_cell_value(s1, 'B1', data.get('year', 2026), typ='n')
            s1 = self._set_cell_value(s1, 'D1', data.get('month', 4), typ='n')
            s1 = self._set_cell_value(s1, 'F1', data.get('day', 16), typ='n')
            # 面積・金額
            s1 = self._set_cell_value(s1, 'B4', data.get('land_area', ''), typ='n')
            s1 = self._set_cell_value(s1, 'B5', data.get('building_area', ''), typ='n')
            s1 = self._set_cell_value(s1, 'B6', data.get('price', ''), typ='n')
            s1 = self._set_cell_value(s1, 'B7', data.get('deposit', ''), typ='n')
            # 有効期間
            s1 = self._set_cell_value(s1, 'B8', data.get('valid_year', 2026), typ='n')
            s1 = self._set_cell_value(s1, 'D8', data.get('valid_month', 5), typ='n')
            s1 = self._set_cell_value(s1, 'F8', data.get('valid_day', 31), typ='n')
            files['xl/worksheets/sheet1.xml'] = s1.encode('utf-8')

            # --- sheet2.xml のキャッシュ値更新（買付証明書シート）---
            s2 = files['xl/worksheets/sheet2.xml'].decode('utf-8')
            # 作成日
            s2 = self._replace_formula_cache(s2, 'W4', 'n', str(data.get('year', 2026)))
            s2 = self._replace_formula_cache(s2, 'AB4', 'n', str(data.get('month', 4)))
            s2 = self._replace_formula_cache(s2, 'AE4', 'n', str(data.get('day', 16)))
            # 物件情報
            s2 = self._replace_formula_cache(s2, 'K17', 'str', data.get('property_name', ''))
            s2 = self._replace_formula_cache(s2, 'K18', 'str', data.get('address', ''))
            s2 = self._replace_formula_cache(s2, 'K19', 'n', str(data.get('land_area', '')))
            s2 = self._replace_formula_cache(s2, 'K20', 'n', str(data.get('building_area', '')))
            # 金額
            s2 = self._replace_formula_cache(s2, 'M22', 'n', str(data.get('price', '')))
            s2 = self._replace_formula_cache(s2, 'M23', 'n', str(data.get('deposit', '')))
            # 有効期間
            s2 = self._replace_formula_cache(s2, 'N27', 'n', str(data.get('valid_year', 2026)))
            s2 = self._replace_formula_cache(s2, 'S27', 'n', str(data.get('valid_month', 5)))
            s2 = self._replace_formula_cache(s2, 'V27', 'n', str(data.get('valid_day', 31)))
            files['xl/worksheets/sheet2.xml'] = s2.encode('utf-8')

            # ZIPとして保存
            with zipfile.ZipFile(self.output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
                for name, content in files.items():
                    zout.writestr(name, content)

            return True

        except Exception as e:
            logger.error(f"Error writing Excel: {e}", exc_info=True)
            return False

    @staticmethod
    def _update_shared_string(xml: str, index: int, new_value: str) -> str:
        """sharedStrings.xmlの指定インデックスの文字列を更新"""
        pattern = r'<si>(.*?)</si>'
        matches = list(re.finditer(pattern, xml, re.DOTALL))
        if index < len(matches):
            m = matches[index]
            new_si = f'<si><t>{re.escape(new_value)}</t></si>'
            xml = xml[:m.start()] + new_si + xml[m.end():]
        return xml

    @staticmethod
    def _set_cell_value(xml: str, cell: str, value, typ: str) -> str:
        """sheet1.xmlの指定セルの値を更新"""
        pattern = rf'(<c r="{cell}"[^>]*>)(?:<v>[^<]*</v>)?'
        repl = rf'\g<1><v>{value}</v>'
        return re.sub(pattern, repl, xml)

    @staticmethod
    def _replace_formula_cache(xml: str, cell: str, typ: str, val: str) -> str:
        """sheet2.xmlのフォーミュラキャッシュ値を静的値に置換"""
        if typ == 'str':
            pattern = rf'(<c r="{cell}"[^>]*>)<f>[^<]*</f><v>[^<]*</v>'
            return re.sub(pattern, rf'\g<1><v>{val}</v>', xml)
        else:
            pattern = rf'<c r="{cell}"([^>]*)><f>[^<]*</f><v>[^<]*</v></c>'
            def repl(m):
                attrs = re.sub(r'\s*t="[^"]*"', '', m.group(1))
                return f'<c r="{cell}"{attrs}><v>{val}</v></c>'
            return re.sub(pattern, repl, xml)
