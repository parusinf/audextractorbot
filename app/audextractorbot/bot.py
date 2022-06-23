import os
import shutil
import tempfile
from os import walk
import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types.message import ContentType
from aiogram.types.input_file import InputFile
from aiogram.types import ParseMode
from app.sys import shell
import config.config as config
from aiogram.bot.api import TelegramAPIServer


# Команды бота
BOT_COMMANDS = '''ping - проверка отклика бота
help - как пользоваться этим ботом?'''

# Create private Bot API server endpoints wrapper
local_server = TelegramAPIServer.from_base(config.BOT_API_SERVER_URL)

# Aiogram Telegram Bot
bot = Bot(token=config.BOT_TOKEN, server=local_server)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# Состояния конечного автомата
class Form(StatesGroup):
    set_tag = State()    # Установить наименование и исполнителя?
    name = State()       # Наименование
    artist = State()     # Артист
    set_image = State()  # Установить картинку?
    image = State()      # Картинка


@dp.message_handler(commands=['help', 'start'])
async def cmd_help(message: types.Message):
    """Что может делать этот бот?"""
    def format_command(command_line):
        command, desc = [x.strip() for x in command_line.split('-')]
        return md.text(md.link(f'/{command}', f'/{command}'), f' - {desc}')

    commands = [format_command(cl) for cl in BOT_COMMANDS.splitlines()]
    await message.reply(
        md.text(
            md.text(f'Поделись со мной ссылкой youtube или rutube, я извлеку для тебя аудио'),
            md.text(md.bold('\nКоманды бота')),
            *commands,
            md.text(md.bold('\nРазработчик')),
            md.text(f'{config.DEVELOPER_NAME} {config.DEVELOPER_TELEGRAM}'),
            md.text(md.bold('\nИсходные коды бота')),
            md.text('[https://github.com/parusinf/audextractorbot]'
                    '(https://github.com/parusinf/audextractorbot)'),
            sep='\n',
        ),
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )


@dp.message_handler(commands='ping')
async def cmd_ping(message: types.Message):
    """Проверка отклика бота"""
    await message.reply('pong')


@dp.message_handler(content_types=ContentType.TEXT)
async def process_url(message: types.Message):
    """markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(['Да', 'Нет'])
    await message.reply('Установить наименование и исполнителя?', reply_markup=markup)"""
    if message.from_user.is_bot:
        await message.reply('Обслуживание ботов не поддерживается')
        return
    dl_message = await message.reply(f'Скачиваю аудио...')
    url = message.text
    dirpath, filename = await get_audio(url, message)
    if filename:
        await message.reply_audio(InputFile(os.path.join(dirpath, filename), filename))
        shutil.rmtree(dirpath)
    else:
        await message.reply('Не получилось скачать аудио')
    await dl_message.delete()


async def get_audio(url, message):
    dirpath = tempfile.mkdtemp()
    format_code = await select_format(url)
    retcode, stdout, stderr = await shell.run_and_logging(f'cd {dirpath}; yt-dlp -f {format_code} {url}')
    if retcode == 0:
        filename = next(walk(dirpath), (None, None, []))[2][0]
        if url.find('rutube') > 0:
            filename_wo_ext = os.path.splitext(filename)[0]
            filename_mp3 = f'{filename_wo_ext}.mp3'
            filepath_mp3 = os.path.join(dirpath, filename_mp3)
            retcode = await shell.run(
                f'ffmpeg -i "{os.path.join(dirpath, filename)}" -codec:a libmp3lame '
                f'-qscale:a {config.QUALITY} "{filepath_mp3}"'
            )
            if retcode == 0:
                filename = filename_mp3
        return dirpath, filename
    else:
        await message.reply(f'{stdout}\n{stderr}')
        return None, None


async def select_format(url):
    if url.find('rutube') > 0:
        retcode, stdout, _ = await shell.run_and_logging(f'yt-dlp -F {url}')
        if retcode == 0:
            format_lines = stdout.splitlines()
            # первая строка в списке форматов с минимальным битрейтом
            format_code = format_lines[7].split(' ')[0]
        else:
            format_code = None
    else:
        format_code = config.TUBE_FORMAT
    return format_code
