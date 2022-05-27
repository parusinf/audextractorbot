from mutagen.mp3 import MP3
import os
import shutil
import tempfile
from os import walk
import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types.message import ContentType
from aiogram.types.input_file import InputFile
from aiogram.types import ParseMode
import config.config as config


# Команды бота
from app.sys import shell

BOT_COMMANDS = '''ping - проверка отклика бота
help - как пользоваться этим ботом?'''

# Aiogram Telegram Bot
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands=['help', 'start'])
async def cmd_help(message: types.Message):
    """Что может делать этот бот?"""
    def format_command(command_line):
        command, desc = [x.strip() for x in command_line.split('-')]
        return md.text(md.link(f'/{command}', f'/{command}'), f' - {desc}')

    commands = [format_command(cl) for cl in BOT_COMMANDS.splitlines()]
    await message.reply(
        md.text(
            md.text(f'Пришлите ссылку с видео'),
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
async def process_results(message: types.Message):
    url = message.text
    dirpath = tempfile.mkdtemp()
    retcode = await shell.run(f'cd {dirpath}; yt-dlp -f 140 {url}')
    if retcode == 0:
        filenames = next(walk(dirpath), (None, None, []))[2]
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            filename_wo_ext = os.path.splitext(filename)[0]
            mp3filename = f'{filename_wo_ext}.mp3'
            mp3filepath = os.path.join(dirpath, mp3filename)
            cmd = f'ffmpeg -i "{filepath}" -codec:a libmp3lame -qscale:a {config.QUALITY} "{mp3filepath}"'
            retcode = await shell.run(cmd)
            if retcode == 0:
                os.remove(filepath)
                mp3size = os.path.getsize(mp3filepath)
                if mp3size > config.CHUNK_SIZE:
                    audio = MP3(mp3filepath)
                    duration = audio.info.length
                    chunk_duration = duration * config.CHUNK_SIZE // mp3size
                    mp3chunk_filename = f'{filename_wo_ext}_%03d.mp3'
                    mp3chunk_filepath = os.path.join(dirpath, mp3chunk_filename)
                    cmd = f'ffmpeg -i "{mp3filepath}" -f segment -segment_time {chunk_duration} ' \
                          f'-c copy "{mp3chunk_filepath}"'
                    retcode = await shell.run(cmd)
                    if retcode == 0:
                        os.remove(mp3filepath)
                        mp3filenames = next(walk(dirpath), (None, None, []))[2]
                        for mp3filename in mp3filenames:
                            mp3filepath = os.path.join(dirpath, mp3filename)
                            await message.reply_document(InputFile(mp3filepath, mp3filename))
                    else:
                        await message.reply_document(InputFile(mp3filepath, mp3filename))
                else:
                    await message.reply_document(InputFile(mp3filepath, mp3filename))
    if retcode != 0:
        await message.reply(f'Код ошибки обработки аудио: {retcode}')
    shutil.rmtree(dirpath)
