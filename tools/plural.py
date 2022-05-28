def seconds(value):
    words = ['секунда', 'секунды', 'секунд']
    if all((value % 10 == 1, value % 100 != 11)):
        return words[0]
    elif all((2 <= value % 10 <= 4,
              any((value % 100 < 10, value % 100 >= 20)))):
        return words[1]
    return words[2]
