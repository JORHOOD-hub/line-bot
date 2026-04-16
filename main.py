#!/usr/bin/env python3
import os
import json
import logging
from flask import Flask, request, abort, send_file
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FileMessage
)
import tempfile
from pathlib import Path

from utils.config import config
from handlers.message_handler import handle_message
from handlers.file_handler import handle_pdf_file

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask アプリケーション初期化
app = Flask(__name__)
config.init_directories()

# LINE Bot API 初期化
line_bot_api = LineBotApi(config.LINE_ACCESS_TOKEN)
webhook_handler = WebhookHandler(config.LINE_CHANNEL_SECRET)


@app.route('/callback', methods=['POST'])
def callback():
    """LINE Webhook エンドポイント"""
    signature = request.headers.get('X-Line-Signature', '')

    try:
        webhook_handler.handle(request.get_data(as_text=True), signature)
    except InvalidSignatureError:
        logger.warning('Invalid signature. Check your channel access token/channel secret.')
        abort(400)

    return 'OK'


@webhook_handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """テキストメッセージ処理"""
    user_id = event.source.user_id
    text = event.message.text

    logger.info(f'Received message from {user_id}: {text}')

    try:
        response_text, pdf_path = handle_message(user_id, text)

        # テキスト応答
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_text)
        )

        # PDF返送（ファイルがある場合）
        if pdf_path and Path(pdf_path).exists():
            send_pdf_to_user(user_id, pdf_path)

    except Exception as e:
        logger.error(f'Error handling message: {e}', exc_info=True)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='申し訳ございません。エラーが発生しました。')
        )


@webhook_handler.add(MessageEvent, message=FileMessage)
def handle_file_message(event):
    """PDFファイル受信処理"""
    user_id = event.source.user_id
    message_id = event.message.id

    logger.info(f'Received file from {user_id}: {message_id}')

    try:
        # LINEからファイルをダウンロード
        message_content = line_bot_api.get_message_content(message_id)

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(message_content.content)
            pdf_path = tmp.name

        logger.info(f'PDF saved to: {pdf_path}')

        # ファイルハンドラーで処理
        response_text = handle_pdf_file(user_id, pdf_path)

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_text)
        )

    except Exception as e:
        logger.error(f'Error handling file: {e}', exc_info=True)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='申し訳ございません。PDFの処理に失敗しました。')
        )


@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return {'status': 'ok'}, 200


@app.route('/pdf/<user_id>', methods=['GET'])
def get_pdf(user_id):
    """生成したPDFをダウンロード"""
    output_dir = Path(config.OUTPUT_DIR)
    pdf_path = output_dir / f"{user_id}_certificate.pdf"

    if not pdf_path.exists():
        logger.warning(f"PDF not found for user {user_id}: {pdf_path}")
        return {'error': 'PDF not found'}, 404

    try:
        logger.info(f"Sending PDF to {user_id}: {pdf_path}")
        return send_file(
            str(pdf_path),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"{user_id}_certificate.pdf"
        )
    except Exception as e:
        logger.error(f"Error sending PDF: {e}", exc_info=True)
        return {'error': 'Failed to send PDF'}, 500


def send_pdf_to_user(user_id: str, pdf_path: str):
    """
    生成したPDFをLINEユーザーに送信
    Flask エンドポイント経由でダウンロードリンクを生成して送信
    """
    try:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            logger.warning(f"PDF file not found: {pdf_path}")
            return

        logger.info(f"PDF ready for {user_id}: {pdf_path}")

        # ダウンロードリンクを生成
        base_url = os.getenv('BASE_URL', 'https://line-bot-production-2689.up.railway.app')
        download_url = f"{base_url}/pdf/{user_id}"

        logger.info(f"Sending download link to {user_id}: {download_url}")

        # ダウンロードリンク付きメッセージを送信
        line_bot_api.push_message(
            user_id,
            TextSendMessage(
                text=f'📄 買付証明書が完成しました！\n\n'
                     f'以下のリンクからダウンロードしてください：\n\n'
                     f'{download_url}'
            )
        )

    except Exception as e:
        logger.error(f'Error sending PDF: {e}', exc_info=True)


@app.errorhandler(400)
def bad_request(error):
    return {'error': 'Bad Request'}, 400


@app.errorhandler(500)
def internal_error(error):
    logger.error(f'Internal server error: {error}', exc_info=True)
    return {'error': 'Internal Server Error'}, 500


if __name__ == '__main__':
    debug = config.FLASK_ENV == 'development'
    app.run(host='0.0.0.0', port=5000, debug=debug)
