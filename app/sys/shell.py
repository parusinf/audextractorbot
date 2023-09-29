import asyncio
import logging
import config.config as config


async def run_and_logging(cmd) -> (int, str, str):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    logging.info(f'[{cmd!r} exited with {proc.returncode}]')
    if config.console_encoding:
        stdout_content = stdout.decode(config.console_encoding)
        stderr_content = stderr.decode(config.console_encoding)
    else:
        stdout_content = stdout
        stderr_content = stderr

    if stdout:
        logging.info(stdout_content)
    if stderr:
        logging.error(stderr_content)

    return proc.returncode, stdout_content, stderr_content


async def run(cmd) -> int:
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()
    return proc.returncode
