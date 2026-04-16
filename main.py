#!/usr/bin/env python3
import os
import json
import logging
from flask import Flask, request, abort
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


def send_pdf_to_user(user_id: str, pdf_path: str):
    """
    生成したPDFをLINEユーザーに送信
    ※ Note: Line Messaging API では push_message で直接バイナリを送信できないため、
    実装上の制限あり。実運用では以下の方法を検討：
    1. CloudStorageで一時ホスト + FileSendMessage（URL指定）
    2. ユーザーがダウンロードリンクをクリック
    """
    try:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            logger.warning(f"PDF file not found: {pdf_path}")
            return

        logger.info(f"PDF ready for {user_id}: {pdf_path}")

        # TODO: Line Messaging API の制限により、以下の実装が必要
        # - CloudStorage (GCS/S3) に PDF をアップロード
        # - 署名付き URL を生成
        # - FileSendMessage で URL を指定

        # 暫定実装：ユーザーがファイルピッカーから取得できるように
        # log してて通知のみ
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text='📄 買付証明書が完成しました！\n\nクライアント側で /output/ フォルダから取得してください。')
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
