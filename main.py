import logging
import signal
import sys
import os
from aiogram import Dispatcher
from aiogram.types import InputFile
from config.config import CERTIFICATE_PATH
from pathlib import Path
from aiogram.utils.executor import start_webhook
import config.config as config
from app.audextractorbot.bot import bot, dp
from app.sys.pid_file import read_pid_file, write_pid_file, remove_pid_file
from app.store.database.models import db

logging.basicConfig(
    filename=config.LOG_FILE if config.USE_LOG_FILE else None,
    level=logging.INFO)


async def on_startup(_: Dispatcher):
    await db.on_connect()
    await bot.set_webhook(
        config.WEBHOOK_URL,
        certificate=InputFile(Path(CERTIFICATE_PATH)),
        drop_pending_updates=True)
    if config.USE_PID_FILE:
        pid_from_os = write_pid_file()
        pid_info = f' pid={pid_from_os}'
    else:
        pid_info = ''
    logging.info(f'audextractorbot запущен{pid_info}')


async def on_shutdown(_: Dispatcher):
    # async_get_audio.stop()
    await bot.set_webhook('')
    await db.on_disconnect()
    if config.USE_PID_FILE:
        pid_from_file = remove_pid_file()
        pid_info = f' pid={pid_from_file}'
    else:
        pid_info = ''
    logging.info(f'audextractorbot остановлен{pid_info}')


def stop(pid):
    try:
        os.kill(pid, signal.SIGINT)
    except ProcessLookupError:
        logging.error(f'Процесс с pid={pid} не найден')


def run(command):
    pid_from_file = read_pid_file()
    if command == 'start':
        if pid_from_file:
            exit()
    elif command == 'stop' and pid_from_file:
        stop(pid_from_file)
        exit()
    elif command == 'restart':
        if pid_from_file:
            stop(pid_from_file)
    else:
        logging.warning(f'Использование: audextractorbot/main.py [start|stop|restart]')


if __name__ == '__main__':
    if config.USE_PID_FILE and len(sys.argv) == 2:
        run(sys.argv[1])
    try:
        start_webhook(
            dispatcher=dp,
            webhook_path=config.WEBHOOK_PATH,
            skip_updates=True,
            host=config.WEBAPP_HOST,
            port=config.WEBAPP_PORT,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
        )
    except Exception as exception:
        if config.USE_PID_FILE:
            remove_pid_file()
        raise exception
