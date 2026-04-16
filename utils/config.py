import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    """アプリケーション設定"""

    # LINE Messaging API
    LINE_CHANNEL_ID = os.getenv('LINE_CHANNEL_ID')
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
    LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')

    # Server
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('DEBUG', 'True') == 'True'
    PORT = int(os.getenv('PORT', 5000))

    # File paths
    BASE_DIR = Path(__file__).parent.parent
    EXCEL_TEMPLATE_PATH = os.getenv('EXCEL_TEMPLATE_PATH', './templates/買付証明書(自動回復済み).xlsm')
    STATE_FILE_PATH = os.getenv('STATE_FILE_PATH', './data/user_states.json')
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', './output')

    # PDF Generation
    GHOSTSCRIPT_PATH = os.getenv('GHOSTSCRIPT_PATH', '/opt/homebrew/bin/gs')
    LIBREOFFICE_PATH = os.getenv('LIBREOFFICE_PATH', '/Applications/LibreOffice.app/Contents/MacOS/soffice')

    # Automation rules
    DEFAULT_DOWN_PAYMENT = 1000000  # 100万円
    DEFAULT_EXPIRATION_DAYS = 45    # 45日後

    @staticmethod
    def init_directories():
        """必要なディレクトリを初期化"""
        Path(Config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(Config.STATE_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)

config = Config()
