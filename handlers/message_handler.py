import re
import os
import logging
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path
from logic.conversation_state import state_manager
from logic.excel_writer import ExcelWriter
from logic.pdf_generator import PDFGenerator
from utils.config import config
from utils.date_utils import parse_price_input
from handlers.修正_handler import handle_修正指示

logger = logging.getLogger(__name__)

def handle_message(user_id: str, text: str) -> tuple:
    """
    ユーザーメッセージを処理し、適切な応答を返す

    返り値: (response_text, pdf_path_or_none)
    """
    user_state = state_manager.get_state(user_id)

    # 状態に応じたメッセージ処理
    if user_state.state == 'waiting_pdf':
        return handle_waiting_pdf(user_id, text), None
    elif user_state.state == 'waiting_price':
        return handle_waiting_price(user_id, text), None
    elif user_state.state == 'waiting_down_payment':
        return handle_waiting_down_payment(user_id, text), None
    elif user_state.state == 'waiting_expiration':
        return handle_waiting_expiration(user_id, text), None
    elif user_state.state == 'generating':
        # PDF生成中のメッセージ（生成完了時はファイル送信）
        pdf_path = user_state.property_data.get('output_pdf_path')
        if pdf_path and Path(pdf_path).exists():
            return "買付証明書が完成しました！", pdf_path
        else:
            return "買付証明書を生成中です...", None
    elif user_state.state == 'completed':
        # 修正指示を検出
        修正キーワード = ['手付金', '購入価格', '物件名', '所在地', '有効期限', '期限', '備考']
        if any(kw in text for kw in 修正キーワード):
            return handle_修正指示(user_id, text)

        # 通常の応答
        pdf_path = user_state.property_data.get('output_pdf_path')
        if pdf_path and Path(pdf_path).exists():
            return "買付証明書を送信します。", pdf_path
        else:
            return "申し訳ございません。ファイルが見つかりません。", None
    else:
        return "申し訳ございません。状態が不明です。最初からやり直してください。", None


def handle_waiting_pdf(user_id: str, text: str) -> str:
    """
    PDF受信待機状態：物件概要書PDFの受信を待つ
    テキストメッセージの場合は案内を返す
    """
    return (
        "こんにちは！買付証明書ボットです。\n"
        "物件概要書のPDFをお送りください。\n"
        "その後、購入価格などの情報をお伺いします。"
    )


def handle_waiting_price(user_id: str, text: str) -> str:
    """
    購入価格入力待機状態
    例：「1000万円」「50000000」など
    """
    price = parse_price_input(text)

    if price is None:
        return (
            "購入価格が認識できませんでした。\n"
            "以下のいずれかの形式でお願いします：\n"
            "- 1000万円\n"
            "- 1億円\n"
            "- 100000000"
        )

    # 購入価格を保存
    state_manager.update_property_data(user_id, 'purchase_price', price)

    # 手付金をデフォルト値で設定（質問しない）
    user_state = state_manager.get_state(user_id)
    state_manager.update_property_data(user_id, 'down_payment', config.DEFAULT_DOWN_PAYMENT)

    # 有効期間を計算
    created_date = datetime.now()
    expiration_date = created_date + timedelta(days=config.DEFAULT_EXPIRATION_DAYS)

    state_manager.update_property_data(user_id, 'created_date', created_date.isoformat())
    state_manager.update_property_data(user_id, 'expiration_date', expiration_date.isoformat())

    # 次の状態へ（waiting_expiration をスキップして直接 generating へ）
    user_state.state = 'generating'
    state_manager.set_state(user_state)

    # PDF生成を実行
    try:
        generate_certificate_pdf(user_id)
        message = (
            f"ありがとうございます！\n"
            f"購入価格：{price:,}円\n"
            f"手付金：{config.DEFAULT_DOWN_PAYMENT:,}円\n"
            f"有効期限：{expiration_date.strftime('%Y年%m月%d日')}\n\n"
            f"買付証明書を生成中です...\n"
            f"少々お待ちください。"
        )
    except Exception as e:
        message = f"申し訳ございません。PDF生成に失敗しました。\n\n{str(e)}"

    return message


def handle_waiting_down_payment(user_id: str, text: str) -> str:
    """
    手付金入力待機状態
    「はい」 or カスタム金額
    """
    user_state = state_manager.get_state(user_id)

    if text.strip() in ['はい', 'Yes', 'yes']:
        # デフォルト値使用
        down_payment = config.DEFAULT_DOWN_PAYMENT
    else:
        # カスタム金額をパース
        down_payment = parse_price_input(text)
        if down_payment is None:
            return (
                "手付金が認識できませんでした。\n"
                "以下のいずれかでお願いします：\n"
                "- はい（100万円で確定）\n"
                "- カスタム金額（例：500万円）"
            )

    # 手付金を保存
    state_manager.update_property_data(user_id, 'down_payment', down_payment)

    # 有効期間を計算
    created_date = datetime.now()
    expiration_date = created_date + timedelta(days=config.DEFAULT_EXPIRATION_DAYS)

    state_manager.update_property_data(user_id, 'created_date', created_date.isoformat())
    state_manager.update_property_data(user_id, 'expiration_date', expiration_date.isoformat())

    # 次の状態へ
    user_state.state = 'waiting_expiration'
    state_manager.set_state(user_state)

    expiration_str = expiration_date.strftime('%Y年%m月%d日')
    return (
        f"手付金：{down_payment:,}円ですね。\n\n"
        f"有効期間を確認します。\n"
        f"本日から45日後：{expiration_str}\n\n"
        f"こちらでよろしいですか？\n\n"
        f"[確認]\n"
        f"[別の日付を指定]"
    )


def handle_waiting_expiration(user_id: str, text: str) -> str:
    """
    有効期間確認待機状態
    「確認」 or 別の日付指定
    """
    user_state = state_manager.get_state(user_id)

    if text.strip() in ['確認', 'OK', 'ok']:
        # 確定して PDF 生成
        user_state.state = 'generating'
        state_manager.set_state(user_state)

        # PDF生成を非同期で実行（実際のボットでは別タスクに）
        try:
            generate_certificate_pdf(user_id)
            message = (
                "ありがとうございます！\n"
                "買付証明書を生成中です...\n"
                "少々お待ちください。"
            )
        except Exception as e:
            message = f"申し訳ございません。PDF生成に失敗しました。\n\n{str(e)}"

        return message
    else:
        # 日付をパース試行（簡易実装）
        return (
            "別の日付指定は現在対応中です。\n"
            "デフォルトの有効期間でお進みください。\n\n"
            "[確認]"
        )


def generate_certificate_pdf(user_id: str) -> Optional[str]:
    """
    買付証明書PDFを生成・保存

    返り値: 生成されたPDFファイルパス（成功時）/ None（失敗時）
    """
    try:
        user_state = state_manager.get_state(user_id)
        property_data = user_state.property_data

        # created_date を datetime に変換
        from dateutil import parser
        created_date = property_data.get('created_date', datetime.now())
        if isinstance(created_date, str):
            created_date = parser.parse(created_date)

        # 生成データを準備
        generate_data = {
            'year': created_date.year,
            'month': created_date.month,
            'day': created_date.day,
            'property_name': property_data.get('property_name', ''),
            'address': property_data.get('location', ''),
            'land_area': property_data.get('land_area', 0),
            'building_area': property_data.get('building_area', 0),
            'price': property_data.get('purchase_price', 0),
            'deposit': property_data.get('down_payment', config.DEFAULT_DOWN_PAYMENT),
            'remarks': property_data.get('remarks', ''),  # 備考
        }

        # 有効期間を追加
        if property_data.get('expiration_date'):
            from dateutil import parser
            exp_date = parser.parse(property_data['expiration_date'])
            generate_data['valid_year'] = exp_date.year
            generate_data['valid_month'] = exp_date.month
            generate_data['valid_day'] = exp_date.day
        else:
            today = datetime.now()
            exp_date = today + timedelta(days=config.DEFAULT_EXPIRATION_DAYS)
            generate_data['valid_year'] = exp_date.year
            generate_data['valid_month'] = exp_date.month
            generate_data['valid_day'] = exp_date.day

        # 出力ファイルパス
        output_dir = Path(config.OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)

        xlsm_path = output_dir / f"{user_id}_certificate.xlsm"
        pdf_path = output_dir / f"{user_id}_certificate.pdf"

        # Step 1: Excel 書き込み
        logger.info(f"Step 1: Writing Excel for user {user_id}")
        writer = ExcelWriter(config.EXCEL_TEMPLATE_PATH, str(xlsm_path))
        if not writer.write_data(generate_data):
            raise Exception("Excel書き込みに失敗しました")
        logger.info(f"Step 1: Excel written successfully")

        # Step 2: PDF 生成（社印入り）
        logger.info(f"Step 2: Generating PDF for user {user_id}")
        generator = PDFGenerator(str(xlsm_path), str(pdf_path))
        if not generator.generate_with_seal():
            raise Exception("PDF生成に失敗しました")
        logger.info(f"Step 2: PDF generated successfully")

        # Step 3: ユーザー状態を更新
        user_state.state = 'completed'
        user_state.property_data['output_pdf_path'] = str(pdf_path)
        state_manager.set_state(user_state)

        # 一時ファイル（XLSM）を削除
        if xlsm_path.exists():
            try:
                os.remove(xlsm_path)
            except:
                pass

        return str(pdf_path)

    except Exception as e:
        logger.error(f"Error generating certificate: {e}", exc_info=True)
        user_state = state_manager.get_state(user_id)
        user_state.state = 'error'
        state_manager.set_state(user_state)
        return None


def create_confirmation_message(property_data: dict) -> str:
    """
    確認メッセージを作成（デバッグ用）
    """
    return (
        f"物件名：{property_data.get('property_name', 'N/A')}\n"
        f"所在地：{property_data.get('location', 'N/A')}\n"
        f"土地面積：{property_data.get('land_area', 'N/A')}㎡\n"
        f"建物面積：{property_data.get('building_area', 'N/A')}㎡\n"
        f"購入価格：{property_data.get('purchase_price', 'N/A'):,}円\n"
        f"手付金：{property_data.get('down_payment', 'N/A'):,}円"
    )
