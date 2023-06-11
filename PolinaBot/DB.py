import random
import sqlite3 as sq
import os
import typing


class User:
    def __init__(self, par):
        self.tg_id, \
        self.username, \
        self.active_msg_id, \
        self.admin_access_lvl, \
        self.timezone, \
        self.time_click, \
        self.time_rand,\
        self.range_rand, \
        self.is_she, \
        self.adding_time_click, \
        self.adding_time_range, \
        self.adding_range, \
        self.setting_tz, \
        self.seen_statuses, \
        self.seen_specials, \
        self.lucky_sends_enabled, \
        self.lucky_sends_sent, \
        self.cur_lucky_sends_count, \
        self.period, \
        self.cur_luck, \
        self.next_max_luck \
            = par


class SQLighter:
    def __init__(self, db_name, sep):
        create = not os.path.exists(db_name)
        self.connection = sq.connect(db_name)
        self.cursor = self.connection.cursor()
        self.sep = sep
        if create:
            tables = {
                'users': [
                    'tg_id',
                    'username',
                    'active_msg_id',
                    'admin_access_lvl',
                    'timezone',
                    'time_click',
                    'time_rand',
                    'range_rand',
                    'is_she',
                    'adding_time_click',
                    'adding_time_range',
                    'adding_range',
                    'setting_tz',
                    'seen_statuses',
                    'seen_specials',
                    'lucky_sends_enabled',
                    'lucky_sends_sent',
                    'cur_lucky_sends_count',
                    'period',
                    'cur_luck',
                    'next_max_luck'
                ],
                'statuses': [
                    'text'
                ],
                'answers': [
                    'text'
                ],
                'specials': [
                    'text'
                ]
            }
            with self.connection:
                for table in tables:
                    self.cursor.execute(f"CREATE TABLE {table}({', '.join([e for e in tables[table]])})")

    """USERS"""

    def add_user(self, tg_id: int, username: str, active_msg_id: int):
        with self.connection:
            self.cursor.execute("INSERT INTO users (tg_id, username, active_msg_id) VALUES (?,?,?)",
                                (tg_id, username, active_msg_id))

    def update_user(self, user: User):
        di = user.__dict__
        with self.connection:
            self.cursor.execute(f"UPDATE users SET {', '.join([f'{k} = ?' for k in di])} "
                                f"WHERE tg_id = {user.tg_id}", [di[k] for k in di])

    def get_user(self, tg_id_or_username: typing.Union[int, str]):
        with self.connection:
            result = self.cursor.execute(f"SELECT * FROM users WHERE "
                                         f"{'tg_id' if type(tg_id_or_username) == int else 'username'} = ?",
                                         (tg_id_or_username,)).fetchone()
        if result is not None:
            return User(result)
        return False

    def get_all_users(self):
        with self.connection:
            result = self.cursor.execute(f"SELECT * FROM users").fetchall()

        final = []
        for r in result:
            final.append(User(r))
        return final

    def remove_user(self, user: User):
        with self.connection:
            self.cursor.execute("DELETE FROM users WHERE tg_id = ?", (user.tg_id,))

    def get_answer(self):
        with self.connection:
            r_count = self.cursor.execute("SELECT COUNT() FROM answers").fetchone()[0]
            result = self.cursor.execute("SELECT text FROM answers WHERE ROWID = ?",
                                         (random.randrange(1, r_count+1, 1),)).fetchone()[0]
        return result

    def get_status(self, user):
        with self.connection:
            r_count = self.cursor.execute("SELECT COUNT() FROM statuses").fetchone()[0]
            if user.seen_statuses:
                choices = list(set(list(range(1, r_count + 1, 1))) - set(map(int, user.seen_statuses.split(self.sep))))
            else:
                choices = list(range(1, r_count + 1, 1))

            if len(choices) <= 1:
                rewrite = True
            else:
                rewrite = False
            rowid = random.choice(choices)
            result = self.cursor.execute("SELECT text FROM statuses WHERE ROWID = ?",
                                         (rowid, )).fetchone()[0]
        return result, str(rowid), rewrite

    def get_special(self, user):
        with self.connection:
            r_count = self.cursor.execute("SELECT COUNT() FROM specials").fetchone()[0]
            if user.seen_specials:
                choices = list(set(list(range(1, r_count + 1, 1))) - set(map(int, user.seen_specials.split(self.sep))))
            else:
                choices = list(range(1, r_count + 1, 1))

            if len(choices) <= 1:
                rewrite = True
            else:
                rewrite = False
            rowid = random.choice(choices)
            result = self.cursor.execute("SELECT text FROM specials WHERE ROWID = ?",
                                         (rowid,)).fetchone()[0]
        return result, str(rowid), rewrite

    def get_all_specials(self):
        with self.connection:
            result = self.cursor.execute("SELECT text FROM specials").fetchall()
        return [r[0] for r in result]

    def get_all_answers(self):
        with self.connection:
            result = self.cursor.execute("SELECT text FROM answers").fetchall()
        return [r[0] for r in result]
