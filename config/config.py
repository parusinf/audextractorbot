import pathlib
import tempfile
import os.path
from config.token import BOT_TOKEN

BASE_DIR = pathlib.Path(__file__).parent.parent
PROGRAM = str(BASE_DIR).split(sep=os.path.sep)[-1]
TEMP_DIR = tempfile.gettempdir()

QUALITY = 7
CHUNK_SIZE = 20 * 1024 * 1024

USE_LOG_FILE = True
LOG_FILE = '/tmp/audextractorbot.log'

USE_PID_FILE = True
PID_FILE = '/tmp/audextractorbot.pid'

CERTIFICATE_PATH = os.path.join(BASE_DIR, 'cert', 'api-parusinf-ru.crt')

# Webhook
WEBHOOK_HOST = 'https://api.parusinf.ru'
WEBHOOK_PATH = f'/bot{BOT_TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

# Web server
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = 5004

# Разработчик
DEVELOPER_NAME = 'Павел Никитин'
DEVELOPER_TELEGRAM = '@nikitinpa'
