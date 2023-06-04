import asyncio
import logging
import config.config as config
from tools.cp1251 import decode_cp1251


async def run_and_logging(cmd) -> (int, str, str):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    logging.info(f'[{cmd!r} exited with {proc.returncode}]')

    if 'Windows' == config.platform_system:
        stdout_content = stdout.decode('cp866')
        stderr_content = stderr.decode('cp866')
    else:
        stdout_content = stdout.decode()
        stderr_content = stderr.decode()

    if stdout:
        logging.info(stdout_content)
    if stderr:
        logging.error(stderr_content)

    return proc.returncode, stdout_content, stderr_content


async def run(cmd) -> int:
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()
    return proc.returncode
