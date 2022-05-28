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
from app.sys import shell, audio
import config.config as config


# Команды бота
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
            md.text(f'Пришлите ссылку с видео на youtube'),
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
    await message.reply(f'Скачиваю и перекодирую аудио...')
    url = message.text
    dirpath = tempfile.mkdtemp()
    retcode = await shell.run(f'cd {dirpath}; yt-dlp -f 140 {url}')
    if retcode == 0:
        filenames = next(walk(dirpath), (None, None, []))[2]
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            chunk_duration = int(audio.get_duration(filepath) * config.CHUNK_SIZE / os.path.getsize(filepath))
            filename_wo_ext, filename_ext = os.path.splitext(filename)
            chunk_name_template = f'{filename_wo_ext}_%02d.{filename_ext}'
            chunk_path_template = os.path.join(dirpath, chunk_name_template)
            retcode = await shell.run(
                f'ffmpeg -i "{filepath}" -f segment -segment_time {chunk_duration} '
                f'-c copy "{chunk_path_template}"'
            )
            if retcode == 0:
                os.remove(filepath)
                chunk_filenames = next(walk(dirpath), (None, None, []))[2]
                for index, chunk_filename in enumerate(chunk_filenames):
                    chunk_filepath = os.path.join(dirpath, chunk_filename)
                    chunk_filename_wo_ext = os.path.splitext(chunk_filename)[0]
                    chunk_filename_mp3 = f'{chunk_filename_wo_ext}.mp3'
                    chunk_filepath_mp3 = os.path.join(dirpath, chunk_filename_mp3)
                    retcode = await shell.run(
                        f'ffmpeg -i "{chunk_filepath}" -codec:a libmp3lame '
                        f'-qscale:a {config.QUALITY} "{chunk_filepath_mp3}"'
                    )
                    if retcode == 0:
                        await message.reply_document(
                            InputFile(chunk_filepath_mp3, chunk_filename_mp3),
                            caption=f'{index+1}/{len(chunk_filenames)}',
                        )
                    else:
                        await message.reply_document(InputFile(chunk_filepath, chunk_filename))
            else:
                await message.reply_document(InputFile(filepath, filename))
    else:
        await message.reply(f'Код ошибки обработки аудио: {retcode}')
    shutil.rmtree(dirpath)
