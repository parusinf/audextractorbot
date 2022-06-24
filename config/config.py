import pathlib
import tempfile
import os.path
from config.token import BOT_TOKEN

BASE_DIR = pathlib.Path(__file__).parent.parent
PROGRAM = str(BASE_DIR).split(sep=os.path.sep)[-1]
TEMP_DIR = tempfile.gettempdir()

TUBE_FORMAT = 140
ENCODE_MP3 = False
QUALITY = 6
THUMB_FILENAME = 'thumb.jpg'
DATABASE_FILE = '/var/lib/sqlite/audextractorbot.db'

USE_LOG_FILE = False
LOG_FILE = '/tmp/audextractorbot.log'

USE_PID_FILE = False
PID_FILE = '/tmp/audextractorbot.pid'

CERTIFICATE_PATH = os.path.join(BASE_DIR, 'cert', 'api-parusinf-ru.crt')

# Webhook
WEBHOOK_HOST = 'https://api.parusinf.ru'
WEBHOOK_PATH = f'/bot{BOT_TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

# Web server
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = 5004

# Telegram Bot API Server
BOT_API_SERVER_URL = 'http://localhost:5000'

# Разработчик
DEVELOPER_NAME = 'Павел Никитин'
DEVELOPER_TELEGRAM = '@nikitinpa'
