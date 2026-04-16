"""
PDFファイル受信・処理ハンドラー
物件概要書PDFから物件情報を抽出してユーザー状態に保存
"""

import os
from pathlib import Path
from logic.conversation_state import state_manager
from logic.pdf_extractor import PDFExtractor

def handle_pdf_file(user_id: str, pdf_path: str) -> str:
    """
    物件概要書PDFを受信・処理

    流程：
    1. PDFから物件情報を抽出
    2. ユーザー状態を「購入価格入力待ち」に変更
    3. 抽出結果を状態に保存
    """
    try:
        # PDFから物件情報を抽出
        extractor = PDFExtractor(pdf_path)
        extracted_data = extractor.extract_data()

        # ユーザーの状態を取得
        user_state = state_manager.get_state(user_id)

        # 抽出したデータを状態に保存
        for key, value in extracted_data.items():
            if value is not None:
                state_manager.update_property_data(user_id, key, value)

        # 状態を「購入価格入力待ち」に変更
        user_state.state = 'waiting_price'
        state_manager.set_state(user_state)

        # 抽出結果を表示
        result_msg = f"""
物件概要書から以下の情報を抽出しました：

物件名：{extracted_data.get('property_name', 'N/A')}
所在地：{extracted_data.get('location', 'N/A')}
土地面積：{extracted_data.get('land_area', 'N/A')}㎡
建物面積：{extracted_data.get('building_area', 'N/A')}㎡

次に、購入価格を入力してください。
（例：1000万円 / 100000000）
""".strip()

        # ファイルをクリーンアップ
        if Path(pdf_path).exists():
            os.remove(pdf_path)

        return result_msg

    except Exception as e:
        # エラー時もファイルをクリーンアップ
        if Path(pdf_path).exists():
            try:
                os.remove(pdf_path)
            except:
                pass

        return f"申し訳ございません。PDFの処理に失敗しました。\n\nエラー: {str(e)}\n\nもう一度お試しください。"
