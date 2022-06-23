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
from app.sys import shell
import config.config as config
from aiogram.bot.api import TelegramAPIServer
import music_tag


# Команды бота
BOT_COMMANDS = '''start - инициализация бота
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


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    await message.answer('Устанавливать заголовок и исполнителя?', reply_markup=markup_yes_no)
    await Form.set_tag.set()


@dp.message_handler(state=Form.set_tag)
async def handle_set_tag(message: types.Message, state: FSMContext):
    set_tag = message.text == 'Да'
    await state.update_data(set_tag=set_tag)
    await state.reset_state(with_data=False)
    # await message.answer('Устанавливать обложку?', reply_markup=markup_yes_no)
    # await Form.set_thumb.set()


@dp.message_handler(state=Form.set_thumb)
async def handle_set_thumb(message: types.Message, state: FSMContext):
    set_thumb = message.text == 'Да'
    await state.update_data(set_thumb=set_thumb)
    await state.reset_state(with_data=False)


@dp.message_handler(state=Form.artist)
async def handle_artist(message: types.Message, state: FSMContext):
    await state.update_data(artist=message.text)
    await message.answer('Заголовок')
    await Form.title.set()


@dp.message_handler(state=Form.title)
async def handle_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    data = await state.get_data()
    if get_value('set_thumb', data):
        await message.answer('Обложка')
        await Form.thumb.set()
    else:
        await send_audio(state)


@dp.message_handler(state=Form.thumb, content_types=ContentType.PHOTO)
async def handle_thumb(message: types.Message, state: FSMContext):
    data = await state.get_data()
    dirpath = get_value('dirpath', data)
    await message.photo[0].download(destination_dir=dirpath)
    await state.update_data(thumb=config.THUMB_FILENAME)
    await send_audio(state)


async def send_audio(state: FSMContext):
    # Подготовка данных
    data = await state.get_data()
    dirpath = get_value('dirpath', data)
    filename = get_value('filename', data)
    filepath = os.path.join(dirpath, filename)
    url_message: types.Message = get_value('url_message', data)
    dl_message = get_value('dl_message', data)
    set_tag = get_value('set_tag', data)

    # Установка тегов
    artist: str = get_value('artist', data)
    title: str = get_value('title', data)
    thumb = get_value('thumb', data)
    thumb_file = InputFile(os.path.join(dirpath, thumb), filename) if thumb else None
    if set_tag:
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

    # Освобождение ресурсов
    shutil.rmtree(dirpath)
    await dl_message.delete()
    data.pop('dirpath', None)
    data.pop('filename', None)
    data.pop('artist', None)
    data.pop('title', None)
    data.pop('thumb', None)
    data.pop('url_message', None)
    data.pop('dl_message', None)
    await state.set_data(data)

    await state.reset_state(with_data=False)


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
            data = await state.get_data()
            if get_value('set_tag', data):
                await message.answer('Исполнитель', reply_markup=types.ReplyKeyboardRemove())
                await Form.artist.set()
            else:
                await send_audio(state)
        else:
            await message.reply('Не получилось скачать аудио')
            await dl_message.delete()
    else:
        await message.reply(f'Поддерживаемые ссылки: {", ".join(SUPPORTED_URLS)}')


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
