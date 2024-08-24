import pathlib
import tempfile
import os.path
from config.secret import BOT_TOKEN
import platform

platform_system = platform.system()

if 'Windows' == platform_system:
    command_sep = ' && '
    console_encoding = 'cp866'
else:
    command_sep = '; '
    console_encoding = ''

BASE_DIR = pathlib.Path(__file__).parent.parent
PROGRAM = str(BASE_DIR).split(sep=os.path.sep)[-1]
TEMP_DIR = tempfile.gettempdir()

YTDLP = '/opt/bin/yt-dlp'
TUBE_FORMAT = 140
ENCODE_MP3 = False
QUALITY = 6
THUMB_FILENAME = 'thumb.jpg'
ERROR_FILE = 'error.log'

USE_LOG_FILE = False
LOG_FILE = '/tmp/audextractorbot.log'

USE_PID_FILE = False
PID_FILE = '/tmp/audextractorbot.pid'

CERTIFICATE_PATH = os.path.join(BASE_DIR, 'cert', 'api-parusinf-ru.crt')

# Webhook
WEBHOOK_HOST = 'https://api.parusinf.ru'
WEBHOOK_PATH = f'/bot{BOT_TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

# Telegram Bot API Server
BOT_API_SERVER_URL = 'http://localhost:8081'

# Разработчик
DEVELOPER_NAME = 'ИП Никитин Павел Александрович'
DEVELOPER_TELEGRAM = '@nikitinpa'
