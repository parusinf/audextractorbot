import asyncio
import os
import shutil
import tempfile
import logging
import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types.message import ContentType
from aiogram.types.input_file import InputFile
from aiogram.types import ParseMode
from app.store.database.tools import human_size
from app.sys import shell
import config.config as config
from aiogram.bot.api import TelegramAPIServer
import music_tag
import app.store.database.models as db


# Команды бота
BOT_COMMANDS = '''tag - настройка установки тегов
stat - статистика
help - как пользоваться этим ботом?'''

SUPPORTED_URLS = ['youtu', 'rutube']

# Create private Bot API server endpoints wrapper
local_server = TelegramAPIServer.from_base(config.BOT_API_SERVER_URL)

# Aiogram Telegram Bot
bot = Bot(token=config.BOT_TOKEN, server=local_server)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


def send_audio_sync(message: types.Message, state: FSMContext, dirpath, _):
    logging.info(dirpath)
    asyncio.run(send_audio(message, state, dirpath))


def get_audio_sync(message: types.Message, state: FSMContext, dirpath, url):
    logging.info(dirpath, url)
    asyncio.run(get_audio(message, state, dirpath, url))


# async_get_audio = AsyncFactory(get_audio_sync, send_audio_sync)

markup_yes_no = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True, one_time_keyboard=True)
markup_yes_no.add('Да', 'Нет')


# Состояния конечного автомата
class Form(StatesGroup):
    set_tag = State()    # Установить исполнителя и заголовок?
    set_thumb = State()  # Установить обложку?
    artist = State()     # Исполнитель
    title = State()      # Заголовок
    thumb = State()      # Обложка


@dp.message_handler(commands=['tag', 'start'])
async def cmd_tag(message: types.Message):
    await message.answer('Устанавливать исполнителя и заголовок аудио?', reply_markup=markup_yes_no)
    await Form.set_tag.set()


@dp.message_handler(state=Form.set_tag)
async def handle_set_tag(message: types.Message, state: FSMContext):
    set_tag = message.text == 'Да'
    user = await get_user(message)
    user.update({'set_tag': set_tag})
    await db.update_user(user)
    await message.reply('/tag - настройка установки тегов')
    data = await state.get_data()
    if get_value('filename', data):
        await Form.artist.set()
    else:
        await state.finish()
    # await message.answer('Устанавливать обложку?', reply_markup=markup_yes_no)
    # await Form.set_thumb.set()


@dp.message_handler(state=Form.set_thumb)
async def handle_set_thumb(message: types.Message, state: FSMContext):
    set_thumb = message.text == 'Да'
    user = await get_user(message)
    user.update({'set_thumb': set_thumb})
    await db.update_user(user)
    await message.reply('/tag - настройка установки тегов', reply_markup=types.ReplyKeyboardRemove())
    await state.finish()


@dp.message_handler(state=Form.artist)
async def handle_artist(message: types.Message, state: FSMContext):
    await state.update_data(artist=message.text)
    await Form.title.set()


@dp.message_handler(state=Form.title)
async def handle_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    user = await get_user(message)
    if user['set_thumb']:
        await message.answer('Обложка')
        await Form.thumb.set()
    else:
        data = await state.get_data()
        dirpath = get_value('dirpath', data)
        await send_audio(message, state, dirpath)


@dp.message_handler(state=Form.thumb, content_types=ContentType.PHOTO)
async def handle_thumb(message: types.Message, state: FSMContext):
    data = await state.get_data()
    dirpath = get_value('dirpath', data)
    await message.photo[0].download(destination_dir=dirpath)
    await state.update_data(thumb=config.THUMB_FILENAME)
    await send_audio(message, state, dirpath)


async def send_audio(message: types.Message, state: FSMContext, dirpath):
    # Проверка наличия скачанного аудио и введённых тегов, если они требуются
    data = await state.get_data()
    filename = get_first_filename(dirpath)
    title = get_value('title', data)
    user = await get_user(message)
    if filename is None or title is None and user['set_tag']:
        return

    # Подготовка остальных данных
    filepath = os.path.join(dirpath, filename)
    artist = get_value('artist', data)
    thumb = get_value('thumb', data)
    thumb_file = InputFile(os.path.join(dirpath, thumb), filename) if thumb else None
    url_message = get_value('url_message', data)
    dl_message = get_value('dl_message', data)

    # Обработка скачанного аудио
    if filename != config.ERROR_FILE:
        # Установка тегов
        if user['set_tag']:
            ext = os.path.splitext(filename)[1]
            new_filename = f'{artist.replace(" ", "_")}__{title.replace(" ", "_")}{ext}'
            new_filepath = os.path.join(dirpath, new_filename)
            os.rename(filepath, new_filepath)
            filename = new_filename
            filepath = new_filepath
            audiofile = music_tag.load_file(filepath)
            audiofile['artist'] = artist
            audiofile['title'] = title
            if thumb:
                with open(os.path.join(dirpath, thumb), 'rb') as img_in:
                    audiofile['artwork'] = img_in.read()
            audiofile.save()

        # Отправка аудио
        await url_message.reply_audio(
            InputFile(filepath, filename),
            performer=artist,
            title=title,
            thumb=thumb_file,
        )

        # Сбор статистики
        dl_count = user['dl_count'] + 1
        dl_size = user['dl_size'] + os.path.getsize(filepath)
        user.update({'dl_count': dl_count, 'dl_size': dl_size})
        await db.update_user(user)
    else:
        with open(filepath, 'r') as text_file:
            text = text_file.read()
        await message.reply(f'Не получилось скачать аудио\n{text}')

    # Освобождение ресурсов
    shutil.rmtree(dirpath)
    await dl_message.delete()
    await state.finish()


async def get_audio(message: types.Message, state: FSMContext, dirpath, url):
    def write_to_file(so, se):
        with open(config.ERROR_FILE, 'w') as text_file:
            text_file.write(f'{so}\n{se}')

    format_code = await select_format(url)
    retcode, stdout, stderr = await shell.run_and_logging(f'cd {dirpath}; yt-dlp -f {format_code} {url}')
    if retcode == 0:
        filename = get_first_filename(dirpath)
        if url.find('rutube') > 0:
            filename_wo_ext = os.path.splitext(filename)[0]
            filename_mp3 = f'{filename_wo_ext}.mp3'
            filepath_mp3 = os.path.join(dirpath, filename_mp3)
            retcode, stdout, stderr = await shell.run_and_logging(
                f'ffmpeg -i "{os.path.join(dirpath, filename)}" -codec:a libmp3lame '
                f'-qscale:a {config.QUALITY} "{filepath_mp3}"'
            )
            if retcode == 0:
                os.remove(filename)
            else:
                write_to_file(stdout, stderr)
    else:
        write_to_file(stdout, stderr)
    return message, state


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


@dp.message_handler(content_types=ContentType.TEXT)
async def handle_url(message: types.Message, state: FSMContext):
    url = message.text
    if url_is_supported(url):
        # Скачивание аудио в параллельном процессе
        dl_message = await message.reply(f'Введите исполнителя и заголовок аудио в отдельных сообщениях')
        dirpath = tempfile.mkdtemp()
        await state.update_data(dirpath=dirpath)
        # async_get_audio.call(message, state, dirpath, url)
        # async_get_audio.wait()
        await get_audio(message, state, dirpath, url)

        # Сохранение сообщения со ссылкой для последующего ответа на него и сообщения о вводе тегов для его удаления
        await state.update_data(url_message=message)
        await state.update_data(dl_message=dl_message)

        # Подготовка тегов
        user = await get_user(message)
        if user['set_tag'] is None:
            await cmd_tag(message)
        elif user['set_tag']:
            await Form.artist.set()
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
            'set_tag': None,
            'set_thumb': None,
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


def get_first_filename(dirpath):
    filenames = next(os.walk(dirpath), (None, None, []))[2]
    return filenames[0] if len(filenames) > 0 else None


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
