import asyncio
import logging


async def run_and_logging(cmd) -> (int, str, str):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    logging.info(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout:
        logging.info(stdout.decode())
    if stderr:
        logging.error(stderr.decode())

    return proc.returncode, stdout.decode(), stderr.decode()


async def run(cmd) -> int:
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()
    return proc.returncode
