from telethon.tl.types import ReplyInlineMarkup, \
    KeyboardButtonCallback as InlineButton, \
    KeyboardButtonRow as Row
from main import cur_cfg

SEP = cur_cfg.sep

"""EXAMPLE OF BUTTON'S DATA"""


# bytes(f'{SEP}'.join(['menu', 'command', data(can be separated by SEP, just write it in next elems)]).encode('UTF-8')


def do_button(title: str, data: list):
    return InlineButton(title, bytes(f'{SEP}'.join(data).encode('UTF-8')))


def do_rows(buttons, rows_count: int = 2):
    r = []
    for i in range(0, len(buttons) - len(buttons) % rows_count, rows_count):
        tmp = []
        for k in range(rows_count):
            tmp.append(buttons[i + k])
        r.append(Row(tmp))

    del buttons[: len(buttons) - len(buttons) % rows_count]

    if buttons:
        r.append(Row(buttons))

    return r


async def make_markup(user, menu: str, data=None):
    butt = []
    match menu:
        case 'main':
            butt = [
                do_button('Время', [menu, 'tz']),
                do_button('Отправка', [menu, 'set_sends']),
                do_button('Цитата сейчас', [menu, 'get_status']),
                do_button('🎱', [menu, 'answer'])
            ]
            if user.admin_access_lvl > 0:
                butt += [
                    do_button('Спец. лист', [menu, 'special_list']),
                    do_button('Лист ответов', [menu, 'answers_list']),
                    do_button('От себя', [menu, 'message'])
                ]
        case 'new':
            butt = [
                do_button('Настроить часовой пояс', [menu, 'set_tz'])
            ]
        case 'confirm':
            butt = [
                do_button('Ок', ['confirm', 'ok'])
            ]
        case 'answer':
            butt = [
                do_button('🎲', [menu, 'get']),
                do_button('Назад', [menu, 'back'])
            ]
        case 'timezone':
            butt = [
                do_button('Поменять', [menu, 'set']),
                do_button('Назад', [menu, 'back'])
            ]
        case 'sends':
            butt = [
                do_button('"Удачливые"', [menu, 'lucky_sends']),
                do_button('"Точные"', [menu, 'click_sends']),
                do_button('Назад', [menu, 'back'])
            ]
        case 'lucky_sends':
            butt = [
                do_button('Настроить количество', [menu, 'set_count']),
                do_button('Настроить период', [menu, 'set_period'])
            ]
            if user.lucky_sends_enabled:
                butt.append(do_button('Выключить', [menu, 'disable']))
            else:
                butt.append(do_button('Включить', [menu, 'enable']))
            butt.append(do_button('Назад', [menu, 'back']))
        case 'add_period':
            if data:
                butt = [
                    do_button('Ок', [menu, 'ok'])
                ]
            else:
                butt = [
                    do_button('Отмена', [menu, 'cancel'])
                ]
        case 'add_count':
            if data:
                butt = [
                    do_button('Ок', [menu, 'ok'])
                ]
            else:
                butt = [
                    do_button('Отмена', [menu, 'cancel'])
                ]
        case 'click_sends':
            butt = [do_button('Добавить', [menu, 'add'])]
            if user.time_click:
                for time in user.time_click.split(SEP):
                    butt.append(do_button(f'Убрать {time}', [menu, 'remove', time]))
            butt.append(do_button('Назад', [menu, 'back']))
        case 'add_click_time':
            if data:
                butt = [
                    do_button('Ок', [menu, 'ok'])
                ]
            else:
                butt = [
                    do_button('Отмена', [menu, 'cancel'])
                ]

    return ReplyInlineMarkup(do_rows(butt))
