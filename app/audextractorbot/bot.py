import os
import shutil
import tempfile
from os import walk
import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types.message import ContentType
from aiogram.types.input_file import InputFile
from aiogram.types import ParseMode
from aiogram.utils.exceptions import MessageToDeleteNotFound

from app.store.database.tools import human_size
from app.sys import shell
import config.config as config
from aiogram.bot.api import TelegramAPIServer
import music_tag
import app.store.database.models as db


# Команды бота
BOT_COMMANDS = '''tag - настройка установки тегов
stat - статистика
reset - удаление настроек
help - как пользоваться этим ботом?'''

SUPPORTED_URLS = ['youtu', 'rutube']

# Create private Bot API server endpoints wrapper
local_server = TelegramAPIServer.from_base(config.BOT_API_SERVER_URL)

# Aiogram Telegram Bot
bot = Bot(token=config.BOT_TOKEN, server=local_server)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

markup_yes_no = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True, one_time_keyboard=True)
markup_yes_no.add('Да', 'Нет')


# Состояния конечного автомата
class Form(StatesGroup):
    set_tag = State()    # Установить исполнителя и заголовок?
    artist = State()     # Исполнитель
    title = State()      # Заголовок


@dp.message_handler(commands=['tag', 'start'])
async def cmd_tag(message: types.Message):
    await message.answer('Устанавливать заголовок и исполнителя?', reply_markup=markup_yes_no)
    await Form.set_tag.set()


@dp.message_handler(state=Form.set_tag)
async def handle_set_tag(message: types.Message, state: FSMContext):
    set_tag = message.text == 'Да'
    user = await get_user(message)
    user.update({'set_tag': set_tag})
    await db.update_user(user)
    await state.finish()


@dp.message_handler(state=Form.artist)
async def handle_artist(message: types.Message, state: FSMContext):
    await save_message(message, state)
    await state.update_data(artist=message.text)
    title_message = await message.answer('Заголовок')
    await save_message(title_message, state)
    await Form.title.set()


@dp.message_handler(state=Form.title)
async def handle_title(message: types.Message, state: FSMContext):
    await save_message(message, state)
    await state.update_data(title=message.text)
    await send_audio(message, state)


async def send_audio(message: types.Message, state: FSMContext):
    # Временный каталог и имя скачанного аудио
    data = await state.get_data()
    dirpath = get_value('dirpath', data)
    filename = get_value('filename', data)
    filepath = os.path.join(dirpath, filename)

    # Установка тегов, если нужно
    artist = get_value('artist', data)
    title = get_value('title', data)
    user = await get_user(message)
    if user['set_tag']:
        ext = os.path.splitext(filename)[1]
        new_filename = f'{artist.replace(" ", "_")}__{title.replace(" ", "_")}{ext}'
        new_filepath = os.path.join(dirpath, new_filename)
        try:
            os.rename(filepath, new_filepath)
        except OSError:
            pass
        filename = new_filename
        filepath = new_filepath
        audiofile = music_tag.load_file(filepath)
        audiofile['artist'] = artist
        audiofile['title'] = title
        audiofile.save()

    # Отправка аудио
    url_message: types.Message = get_value('url_message', data)
    await url_message.reply_audio(InputFile(filepath, filename), performer=artist, title=title)

    # Сбор статистики
    dl_count = user['dl_count'] + 1
    dl_size = user['dl_size'] + os.path.getsize(filepath)
    user.update({'dl_count': dl_count, 'dl_size': dl_size})
    await db.update_user(user)

    # Освобождение ресурсов
    shutil.rmtree(dirpath)
    await delete_messages(state)
    await state.finish()


@dp.message_handler(commands=['stat'])
async def cmd_stat(message: types.Message):
    user = await get_user(message)
    total_dl_count, total_dl_size = await db.get_stat()
    await message.answer(
        f'Количество: {user["dl_count"]}\n'
        f'Объём: {human_size(user["dl_size"])}\n'
        f'Общее количество: {total_dl_count}\n'
        f'Общий объём: {human_size(total_dl_size)}'
    )


@dp.message_handler(commands=['reset'])
async def cmd_reset(message: types.Message):
    await db.delete_user(message.from_user.id)
    await message.answer('Настройки удалены')


@dp.message_handler(commands='help')
async def cmd_help(message: types.Message):
    """Что может делать этот бот?"""
    def format_command(command_line):
        command, desc = [x.strip() for x in command_line.split('-')]
        return md.text(md.link(f'/{command}', f'/{command}'), f' - {desc}')

    commands = [format_command(cl) for cl in BOT_COMMANDS.splitlines()]
    await message.reply(
        md.text(
            md.text(f'Поделись ссылкой с ботом для извлечения аудио'),
            md.text(md.bold('\nКоманды бота')),
            *commands,
            md.text(md.bold('\nОшибки и пожелания сообщайте разработчику')),
            md.text(f'{config.DEVELOPER_NAME} {config.DEVELOPER_TELEGRAM}'),
            md.text(md.bold('\nИсходные коды бота')),
            md.text('[https://github.com/parusinf/audextractorbot]'
                    '(https://github.com/parusinf/audextractorbot)'),
            sep='\n',
        ),
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def save_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'messages' in data:
        messages = data['messages']
    else:
        messages = []
    messages.append(message)
    await state.update_data(messages=messages)


async def delete_messages(state: FSMContext):
    data = await state.get_data()
    if 'messages' in data:
        messages = data['messages']
        if messages:
            for message in messages:
                try:
                    await message.delete()
                except MessageToDeleteNotFound:
                    pass
            data.pop('messages')
            await state.update_data(data)


@dp.message_handler(content_types=ContentType.TEXT)
async def handle_url(message: types.Message, state: FSMContext):
    await state.update_data(url_message=message)
    url = message.text
    if url_is_supported(url):
        # Сообщение о скачивании
        download_message = await message.reply(f'Скачиваю аудио...')
        await save_message(download_message, state)

        # Временный каталог для скачивания
        dirpath = tempfile.mkdtemp()
        await state.update_data(dirpath=dirpath)

        # Скачивание аудио
        filename = await get_audio(url, dirpath, message)
        await state.update_data(filename=filename)

        if filename:
            # Установка тегов, если нужно
            user = await get_user(message)
            if user['set_tag']:
                artist_message = await message.answer('Исполнитель', reply_markup=types.ReplyKeyboardRemove())
                await save_message(artist_message, state)
                await Form.artist.set()
            # Отправка аудио
            else:
                await send_audio(message, state)
        else:
            await message.reply('Не получилось скачать аудио')
            await delete_messages(state)
    else:
        await message.reply(f'Поддерживаемые ссылки: {", ".join(SUPPORTED_URLS)}')


async def get_user(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        user = {
            'user_id': message.from_user.id,
            'username': message.from_user.username,
            'user_first_name': message.from_user.first_name,
            'user_last_name': message.from_user.last_name,
            'set_tag': False,
            'dl_count': 0,
            'dl_size': 0,
        }
        await db.insert_user(user)
    return user


def url_is_supported(url):
    is_supported = False
    for u in SUPPORTED_URLS:
        if url.find(u) > 0:
            is_supported = True
            break
    return is_supported


def get_value(key, data):
    return data[key] if key in data else None


async def get_audio(url, dirpath, message):
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
        return filename
    else:
        await message.reply(f'{stdout}\n{stderr}')
        return None


async def select_format(url):
    if url.find('rutube') > 0:
        retcode, stdout, _ = await shell.run_and_logging(f'yt-dlp -F {url}')
        if retcode == 0:
            format_lines = stdout.splitlines()
            header_line_index = 8
            for i, line in enumerate(format_lines):
                if line[:2] == 'ID':
                    header_line_index = i
                    break
            # первая строка в списке форматов с минимальным битрейтом
            format_code = format_lines[header_line_index+2].split(' ')[0]
        else:
            format_code = None
    else:
        format_code = config.TUBE_FORMAT
    return format_code
