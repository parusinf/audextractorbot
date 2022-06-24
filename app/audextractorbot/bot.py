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
from app.store.database.tools import human_size, SizeUnit
from app.sys import shell
import config.config as config
from aiogram.bot.api import TelegramAPIServer
import music_tag
import app.store.database.models as db


# Команды бота
BOT_COMMANDS = '''tag - настройка установки тегов
stat - статистика
ping - проверка отклика бота
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
    set_thumb = State()  # Установить обложку?
    artist = State()     # Исполнитель
    title = State()      # Заголовок
    thumb = State()      # Обложка


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
    await message.reply('/tag - настройка установки тегов')
    data = await state.get_data()
    if get_value('filename', data):
        await message.answer('Исполнитель', reply_markup=types.ReplyKeyboardRemove())
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
    await message.answer('Заголовок')
    await Form.title.set()


@dp.message_handler(state=Form.title)
async def handle_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    user = await get_user(message)
    if user['set_thumb']:
        await message.answer('Обложка')
        await Form.thumb.set()
    else:
        await send_audio(message, state)


@dp.message_handler(state=Form.thumb, content_types=ContentType.PHOTO)
async def handle_thumb(message: types.Message, state: FSMContext):
    data = await state.get_data()
    dirpath = get_value('dirpath', data)
    await message.photo[0].download(destination_dir=dirpath)
    await state.update_data(thumb=config.THUMB_FILENAME)
    await send_audio(message, state)


async def send_audio(message: types.Message, state: FSMContext):
    # Подготовка данных
    data = await state.get_data()
    dirpath = get_value('dirpath', data)
    filename = get_value('filename', data)
    filepath = os.path.join(dirpath, filename)
    url_message: types.Message = get_value('url_message', data)
    dl_message = get_value('dl_message', data)
    user = await get_user(message)

    # Установка тегов
    artist = get_value('artist', data)
    title = get_value('title', data)
    thumb = get_value('thumb', data)
    thumb_file = InputFile(os.path.join(dirpath, thumb), filename) if thumb else None
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

    # Освобождение ресурсов
    shutil.rmtree(dirpath)
    await dl_message.delete()
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


@dp.message_handler(commands='ping')
async def cmd_ping(message: types.Message):
    """Проверка отклика бота"""
    await message.reply('pong')


@dp.message_handler(content_types=ContentType.TEXT)
async def handle_url(message: types.Message, state: FSMContext):
    if message.from_user.is_bot:
        await message.reply('Обслуживание ботов не поддерживается')
        return
    url = message.text
    if url_is_supported(url):
        dl_message = await message.reply(f'Скачиваю аудио...')
        dirpath = tempfile.mkdtemp()
        await state.update_data(dirpath=dirpath)
        filename = await get_audio(url, dirpath, message)
        await state.update_data(url_message=message)
        await state.update_data(dl_message=dl_message)
        await state.update_data(filename=filename)
        if filename:
            user = await get_user(message)
            if user['set_tag'] is None:
                await cmd_tag(message)
            elif user['set_tag']:
                await message.answer('Исполнитель', reply_markup=types.ReplyKeyboardRemove())
                await Form.artist.set()
            else:
                await send_audio(message, state)
        else:
            await message.reply('Не получилось скачать аудио')
            await dl_message.delete()
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
            # первая строка в списке форматов с минимальным битрейтом
            format_code = format_lines[7].split(' ')[0]
        else:
            format_code = None
    else:
        format_code = config.TUBE_FORMAT
    return format_code
