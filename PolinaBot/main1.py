import asyncio
import logging
import re
import random as r

from geopy import geocoders
from geopy.extra.rate_limiter import RateLimiter
from timezonefinder import TimezoneFinder
import datetime as dt
import pytz

from settings import Config
from DB import SQLighter
import keyboards as kb

from telethon import TelegramClient, events, Button
from telethon.errors import MessageDeleteForbiddenError, MessageIdInvalidError, MessageNotModifiedError

logging.basicConfig(level=logging.INFO)

cur_cfg = Config()
db = SQLighter(cur_cfg.db_name, cur_cfg.sep)
bot = TelegramClient(cur_cfg.bot_session_name, cur_cfg.api_id, cur_cfg.api_hash)

geo = geocoders.Nominatim(user_agent="WellMot")
reverse = RateLimiter(geo.geocode, min_delay_seconds=1)
tz_find = TimezoneFinder()

SEP = cur_cfg.sep


async def utc_to_local(utc_now, tz_zone):
    tz = pytz.timezone('UTC' if tz_zone is None else tz_zone)
    return pytz.utc.localize(utc_now, is_dst=None).astimezone(tz)


async def send_status(user):
    text, rowid, need_rewrite = db.get_status(user)
    if user.seen_statuses and not need_rewrite:
        tmp = user.seen_statuses.split(SEP)
        tmp.append(rowid)
        user.seen_statuses = SEP.join(tmp)
    else:
        user.seen_statuses = rowid

    db.update_user(user)
    await bot.send_message(user.tg_id, text)
    return


async def send_special(user):
    text, rowid, need_rewrite = db.get_special(user)
    if user.seen_specials and not need_rewrite:
        tmp = user.seen_specials.split(SEP)
        tmp.append(rowid)
        user.seen_specials = SEP.join(tmp)
    else:
        user.seen_specials = rowid

    db.update_user(user)
    await bot.send_message(user.tg_id, text)
    return


async def main_menu(event, user, replace: bool = False, new: bool = False):
    if new:
        text = 'Привет🙂\n' \
               'Я - бот, написанный для важного человека в жизни одного программиста.\n\n' \
               'Я буду присылать тебе сообщения, ' \
               'которые будут поднимать тебе настроение и заряжать силами на весь день :)\n\n' \
               'Если будет слишком тяжело, можешь нажать на 🎱.\n\n' \
               'Люблю тебя 🧡'
        butt = await kb.make_markup(user, 'new')
    else:
        if user.setting_tz:
            await event.delete()
            try:
                await bot.edit_message(user.tg_id, user.active_msg_id,
                                       "Чтобы понять, когда отправлять сообщения, нужно сверить часы. "
                                       "Не жульничай :/\n\n"
                                       "Отправь название города, в котором ты сейчас)")
            except MessageNotModifiedError:
                await bot.edit_message(user.tg_id, user.active_msg_id,
                                       "Если пошутить одну шутку два раза подряд, смешнее не станет :/\n\n"
                                       "Отправь название города, в котором ты сейчас)")
            return

        text = 'Давай посмотрим, что можно сделать)\n\n'
        butt = await kb.make_markup(user, 'main')

    user.setting_tz = 0
    user.adding_range = 0
    user.adding_time_range = 0
    user.adding_time_click = 0
    db.update_user(user)

    if replace:
        msg_sent = await bot.send_message(event.sender, text, buttons=butt,
                                          link_preview=False)
        await event.delete()
        try:
            await bot.delete_messages(event.sender, user.active_msg_id)
        except (MessageIdInvalidError, MessageDeleteForbiddenError):
            pass
        user.active_msg_id = msg_sent.id
        db.update_user(user)
        return

    await bot.edit_message(user.tg_id, await event.get_message(), text, buttons=butt,
                           link_preview=False)
    return


@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = db.get_user(event.sender.id)
    if not user:
        db.add_user(event.sender.id, event.sender.username, event.message.id)
        user = db.get_user(event.sender.id)
        await main_menu(event, user, True, True)
        return
    else:
        await main_menu(event, user, True)
        return


@bot.on(events.NewMessage(pattern='/admin'))
async def admin_start(event):
    return


@bot.on(events.NewMessage())
async def user_input(event):
    if event.message.text == '/start' or event.message.text == '/admin':
        return
    user = db.get_user(event.sender.id)
    if not user:
        await start(event)
        return

    if user.setting_tz:
        await event.delete()
        place, (lat, lng) = reverse(event.message.text)
        tz_zone = tz_find.timezone_at(lng=lng, lat=lat)
        tz = pytz.timezone(tz_zone)
        utc_now = dt.datetime.utcnow()
        local_now = pytz.utc.localize(utc_now, is_dst=None).astimezone(tz)
        text = f'Итак, сейчас ты в местечке под названием `{place.partition(",")[0]}`\n' \
               f'Тогда у тебя должно быть `{local_now.strftime("%H:%M")}`\n' \
               f'В любой момент можно изменить это в меню "Время".'
        butt = await kb.make_markup(user, 'confirm')
        user.setting_tz = 0
        user.timezone = tz_zone
        db.update_user(user)
        await bot.edit_message(user.tg_id, user.active_msg_id, text, buttons=butt)
        return
    if user.adding_time_range:
        period_sample = re.compile(r'^(2[0-3]|[0-1]?\d)\W([0-5]\d)\W(2[0-3]|[0-1]?\d)\W([0-5]\d)$')
        await event.delete()
        if period_sample.match(event.message.text):
            nums = re.split(r'\W', event.message.text)
            user.time_rand = f'{nums[0]}:{nums[1]}-{nums[2]}:{nums[3]}'
            user.adding_time_range = 0
            db.update_user(user)
            await bot.edit_message(user.tg_id, user.active_msg_id, "Успешно!",
                                   buttons=await kb.make_markup(user, 'add_period', 1))
            return
        else:
            try:
                await bot.edit_message(user.tg_id, user.active_msg_id, 'Не соответствует представлению времени. '
                                                                       'Попробуй ещё раз, у тебя получится, '
                                                                       'я в тебя верю)')
            except MessageNotModifiedError:
                await bot.edit_message(user.tg_id, user.active_msg_id,
                                       'Серьёзно?)\nНа второй раз ведь точно должно сработать, не так ли?)')
            return
    if user.adding_range:
        range_sample = re.compile(r'^([0-4]?\d)\W([0-4]?\d)$')
        await event.delete()
        if range_sample.match(event.message.text):
            nums = re.split(r'\W', event.message.text)
            user.range_rand = f'{min(nums)}{SEP}{max(nums)}'
            user.adding_range = 0
            db.update_user(user)
            await bot.edit_message(user.tg_id, user.active_msg_id, "Успешно!",
                                   buttons=await kb.make_markup(user, 'add_count', 1))
            return
        else:
            try:
                await bot.edit_message(user.tg_id, user.active_msg_id, 'Ой! Что-то не так. Там ошибочка была...\n'
                                                                       'А я уже кнопочку нажал, и всё удалилось 🥲\n'
                                                                       'Придётся тебе писать заново🤷‍♂️',
                                       buttons=await kb.make_markup(user, 'add_count'))
            except MessageNotModifiedError:
                await bot.edit_message(user.tg_id, user.active_msg_id,
                                       'А я смотрю, ты стоишь на своём!\n'
                                       'Молодец)\n'
                                       'Но, у меня есть чёткий алгоритм, который никак не обойти...\n'
                                       'Подчинись, пожалуйста 🥺',
                                       buttons=await kb.make_markup(user, 'add_count'))
        return
    if user.adding_time_click:
        time_sample = re.compile(r'^(2[0-3]|[0-1]?\d)\W([0-5]\d)$')
        await event.delete()
        if time_sample.match(event.message.text):
            nums = re.split(r'\W', event.message.text)
            if user.time_click:
                tmp = user.time_click.split(SEP)
                tmp.append(f'{nums[0]}:{nums[1]}')
                user.time_click = SEP.join(tmp)
            else:
                user.time_click = f'{nums[0]}:{nums[1]}'
            user.adding_time_click = 0
            db.update_user(user)
            await bot.edit_message(user.tg_id, user.active_msg_id, "Успешно!",
                                   buttons=await kb.make_markup(user, 'add_click_time', 1))
            return

        else:
            try:
                await bot.edit_message(user.tg_id, user.active_msg_id, 'Давай по-новой, Миша, всё хуйня.',
                                       buttons=await kb.make_markup(user, 'add_click_time'))
            except MessageNotModifiedError:
                await bot.edit_message(user.tg_id, user.active_msg_id,
                                       'Ти шо, хохол?',
                                       buttons=await kb.make_markup(user, 'add_click_time'))

    return


@bot.on(events.CallbackQuery())
async def query_process(event):
    user = db.get_user(event.query.peer.user_id)
    if not user:
        await start(event)
        return
    data = event.data.decode('UTF-8')
    menu, s, data = data.partition(SEP)
    command, s, data = data.partition(SEP)

    # Place for inline menu defs
    async def answer_menu(show_ans: bool = False):
        try:
            text_lol = '**8й шар**\n\n'
            if show_ans:
                text_lol += f'`{db.get_answer()}`\n\n'
            else:
                text_lol += 'Держи в голове вопрос, на который можно ответить `Да` или `Нет`, и нажми на 🎲\n\n'

            text_lol += 'Помни, что это не призыв к действию. Это лишь пёрышко, падающее на весы принятие решения!'
            await bot.edit_message(user.tg_id, user.active_msg_id, text_lol,
                                   buttons=await kb.make_markup(user, 'answer'))
            return
        except MessageNotModifiedError:
            await answer_menu(True)
            return

    async def timezone_menu():
        local_now = await utc_to_local(dt.datetime.utcnow(), user.timezone)
        text_lol = f'Время сейчас: `{local_now.strftime("%H:%M")}`\n' \
                   f'Часовой пояс: {user.timezone}'
        await bot.edit_message(user.tg_id, user.active_msg_id, text_lol,
                               buttons=await kb.make_markup(user, 'timezone'))

    async def sends_menu():
        text_lol = f'🍀 **"Удачливые" цитатки:**\n\n'
        if user.range_rand and user.time_rand and user.lucky_sends_enabled:
            x, s_t, y = user.range_rand.partition(SEP)
            st, s_t, en = user.time_rand.partition('-')
            text_lol += f'От `{x}` до `{y}` раз с `{st}` по `{en}`.\n\n'
        else:
            text_lol += 'Отключены.\n\n'

        text_lol += '🎯 **"Точные" цитатки:**\n\n'
        if user.time_click:
            text_lol += "\n".join(user.time_click.split(SEP)) + '\n\n'
        else:
            text_lol += 'Отключены.\n\n'

        await bot.edit_message(user.tg_id, user.active_msg_id, text_lol, buttons=await kb.make_markup(user, 'sends'))
        return

    async def lucky_sends():
        text_lol = f'🍀 **"Удачливые" цитатки:**\n\n'
        text_lol += 'Статус: ' + ('Включены' if user.lucky_sends_enabled else 'Выключены') + '\n'
        text_lol += 'Количество: '
        if user.range_rand:
            x, s_t, y = user.range_rand.partition(SEP)
            text_lol += f'от {x} до {y}\n'
        else:
            text_lol += 'Не настроено.\n'
        text_lol += 'Период: '
        if user.time_rand:
            st, s_t, en = user.time_rand.partition('-')
            text_lol += f'с {st} по {en}\n'
        else:
            text_lol += 'Не настроено.\n'

        await bot.edit_message(user.tg_id, user.active_msg_id, text_lol,
                               buttons=await kb.make_markup(user, 'lucky_sends'))
        return

    async def click_sends():
        text_lol = '🎯 **"Точные" цитатки:**\n\n'
        if user.time_click:
            text_lol += "\n".join(user.time_click.split(SEP)) + '\n\n'
        else:
            text_lol += 'Отключены.\n\n'
        await bot.edit_message(user.tg_id, user.active_msg_id, text_lol,
                               buttons=await kb.make_markup(user, 'click_sends'))
        return

    async def special_menu():
        text_lol = 'СПЕЦИАЛЬНЫЕ ЦИТАТЫ\n\n'
        specials = db.get_all_specials()
        if len(specials) < 50:
            text_lol += '\n'.join(specials)
        else:
            text_lol += '> (=) 50'

        await bot.edit_message(user.tg_id, user.active_msg_id, text_lol, buttons=await kb.make_markup(user, 'special'))
        return

    async def answers_menu():
        text_lol = 'ОТВЕТЫ\n\n'
        answers = db.get_all_answers()
        if len(answers) < 50:
            text_lol += '\n'.join(answers)
        else:
            text_lol += '> (=) 50'

        await bot.edit_message(user.tg_id, user.active_msg_id, text_lol, buttons=await kb.make_markup(user, 'answers'))
        return

    """PRIORITY BUTTONS"""
    if command == 'cancel':
        if menu == 'add_period':
            user.adding_time_range = 0
            db.update_user(user)
            await lucky_sends()
            return
        if menu == 'add_count':
            user.adding_range = 0
            db.update_user(user)
            await lucky_sends()
            return
        if menu == 'add_click_time':
            user.adding_time_click = 0
            db.update_user(user)
            await click_sends()
            return
        return
    if command == 'back':
        if menu == 'answer' or menu == 'timezone' or menu == 'sends':
            await main_menu(event, user)
            return
        if menu == 'lucky_sends' or menu == 'click_sends':
            await sends_menu()
            return
        return
    if command == 'main':
        return
    if command == 'ok':
        if menu == 'confirm':
            await main_menu(event, user)
            return
        if menu == 'add_period' or menu == 'add_count':
            await lucky_sends()
            return
        if menu == 'add_click_time':
            await click_sends()
            return
        return

    "MENU LOGIC"
    if menu == 'new':
        if command == 'set_tz':
            await bot.edit_message(user.tg_id, user.active_msg_id, 'Окей.\nНапиши мне свой город, пожалуйста)')
            user.setting_tz = True
            db.update_user(user)
            return
        return

    if menu == 'main':
        if command == 'tz':
            await timezone_menu()
            return
        if command == 'set_sends':
            await sends_menu()
            return
        if command == 'answer':
            await answer_menu()
            return
        if command == 'get_status':
            await send_status(user)
            return
        if command == 'special_list':
            await special_menu()
            return
        if command == 'answers_list':
            await answer_menu()
            return
        return

    if menu == 'answer':
        if command == 'get':
            await answer_menu(True)
            return
        return

    if menu == 'timezone':
        if command == 'set':
            user.setting_tz = 1
            db.update_user(user)
            await bot.edit_message(user.tg_id, user.active_msg_id, "Окей. Напиши мне город, в котором ты сейчас :)")
            return
        return

    if menu == 'sends':
        if command == 'lucky_sends':
            await lucky_sends()
            return
        if command == 'click_sends':
            await click_sends()
            return

    if menu == 'lucky_sends':
        if command == 'set_period':
            await bot.edit_message(user.tg_id, user.active_msg_id,
                                   "Я умный)\n"
                                   "Мне нужно сообщение со временем начала\n"
                                   "(от 0 до 12 часов и от 0 до 59 минут)\n"
                                   "И временем конца (такая же штука)\n"
                                   "А что будет между ними и между часами и минутами - как удобно тебе, "
                                   "я пойму, главное, чтобы не цифра и не буква)",
                                   buttons=await kb.make_markup(user, 'add_period'))
            user.adding_time_range = 1
            db.update_user(user)
            return
        if command == 'set_count':
            text = 'Руки вверх!\n' \
                   'Мне нужны цифры. Те, которые показывают минимальное и максимальное приемлемое ' \
                   'количество сообщений от меня в день.\n\n' \
                   'Но есть подвох, минимальное должно быть не меньше 1, а максимальное - не больше 49.\n' \
                   'Последнее, что я хочу - это сидеть в тюрячке для ботов за спам...\n' \
                   'Знаешь, что делают в тюрячьке? - Долбят в задницу. ' \
                   'А у меня и так уже сокет расшатан...'
            user.adding_range = 1
            db.update_user(user)
            await bot.edit_message(user.tg_id, user.active_msg_id, text,
                                   buttons=await kb.make_markup(user, 'add_count'))
            return
        if command == 'enable':
            user.lucky_sends_enabled = 1
            db.update_user(user)
            await lucky_sends()
            return
        if command == 'disable':
            user.lucky_sends_enabled = 0
            db.update_user(user)
            await lucky_sends()
            return

    if menu == 'click_sends':
        if command == 'remove':
            tmp = user.time_click.split(SEP)
            tmp.remove(data)
            user.time_click = SEP.join(tmp)
            db.update_user(user)
            await click_sends()
            return
        if command == 'add':
            await bot.edit_message(user.tg_id, user.active_msg_id,
                                   'Мне нужно время в формате: \n'
                                   'Часы (0-23) минуты (00-59)\n'
                                   'И между ними любой символ,'
                                   'но не цифра и не буква.\n'
                                   'Что-то типа `10=00`\n'
                                   'Вот тебе и задачка подкатила...',
                                   buttons=await kb.make_markup(user, 'add_click_time'))
            user.adding_time_click = 1
            db.update_user(user)
            return
        return

    if menu == 'special_list':
        await special_menu()
        return

    if menu == 'answers_list':
        await answer_menu()
        return

    if menu == 'message':
        await bot.edit_message(user.tg_id, user.active_msg_id,
                               'Что пишем ей?', buttons=await kb.make_markup(user, 'write_message'))
        user.writing_message = 1
        db.update_user(user)
        return


async def click_statuses(us):
    now = dt.datetime.utcnow()
    for u in us:
        if not u.timezone or not u.time_click:
            continue
        tz = u.timezone
        local_now = (await utc_to_local(now, tz)).strftime("%H:%M")
        times = u.time_click.split(SEP)
        for t in times:
            if local_now == t:
                await send_status(u)


async def lucky_statuses(us):
    now = dt.datetime.utcnow()
    for u in us:
        if not u.timezone or not u.time_rand or not u.range_rand or not u.lucky_sends_enabled:
            continue
        tz = u.timezone
        local_now = (await utc_to_local(now, tz)).replace(second=0, microsecond=0)
        st, s_, en = u.time_rand.partition('-')
        st = local_now.replace(hour=int(st.partition(':')[0]), minute=int(st.partition(':')[2]))
        en = local_now.replace(hour=int(en.partition(':')[0]), minute=int(en.partition(':')[2]))
        if local_now > st >= en:
            en += dt.timedelta(days=1)
        if st >= en > local_now:
            st -= dt.timedelta(days=1)

        if local_now == st:
            u.lucky_sends_sent = 0
            u.cur_lucky_sends_count = r.randrange(int(u.range_rand.partition(SEP)[0]),
                                                  int(u.range_rand.partition(SEP)[2] + 1), 1)
            db.update_user(u)
            continue

        if en >= local_now > st:
            if u.cur_lucky_sends_count is None:
                u.cur_lucky_sends_count = 10
                db.update_user(u)
            if u.lucky_sends_sent is None:
                u.lucky_sends_sent = 0
                db.update_user(u)

            if u.lucky_sends_sent < u.cur_lucky_sends_count and \
                    r.choices([True, False], weights=[u.cur_lucky_sends_count - u.lucky_sends_sent,
                                                      (((en - local_now).seconds // 60) % 60) + 1])[0]:
                if u.is_she and r.choices([True, False], weights=[10, 50])[0]:
                    await send_special(u)
                else:
                    await send_status(u)
                u.lucky_sends_sent += 1
                db.update_user(u)


async def send_activity():
    while True:
        await asyncio.sleep(60)
        users = db.get_all_users()
        await asyncio.gather(click_statuses(users),
                             lucky_statuses(users))


if __name__ == "__main__":
    bot.start(bot_token=cur_cfg.bot_token)
    bot.loop.create_task(send_activity())
    bot.loop.run_forever()
