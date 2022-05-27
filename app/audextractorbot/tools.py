from datetime import timedelta


async def echo_error(message, error):
    error_message = error or 'Пропущено сообщение об ошибке'
    await message.reply(error_message)
    from logging import error
    error(error_message)


def ptimedelta(time_str: str):
    """
    Разбор временного отрезка
    :param time_str: строка в формате ММ:СС или ЧЧ:ММ:СС
    :return: объект timedelta
    """
    if len(time_str) == 5:
        time_str = f'00:{time_str}'
    hours, minutes, seconds = tuple([int(t) for t in time_str.split(':')])
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def ftimedelta(time: timedelta):
    """
    Форматирование временного отрезка
    :param time: объект timedelta
    :return: строка в формате ММ:СС или ЧЧ:ММ:СС
    """
    hours = time.seconds // 3600
    minutes = time.seconds // 60 - hours * 60
    seconds = time.seconds % 60
    minutes_str = f'{str(minutes).zfill(2)}:{str(seconds).zfill(2)}'
    if hours == 0:
        return minutes_str
    else:
        return f'{str(hours).zfill(2)}:{minutes_str}'
