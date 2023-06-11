import datetime as dt
import time
import random as r

end_time = dt.datetime.now().replace(second=0, microsecond=0) + dt.timedelta(minutes=5)
print(end_time)

lucky_sends_sent = 0
now = dt.datetime.now()
while now < end_time:
    weights = [10 - lucky_sends_sent,
               (((end_time - now).seconds // 60) % 60) + 1]
    print()
    print(weights)
    ch = r.choices([True, False],
                   weights=weights)[0]
    now = dt.datetime.now()
    print(ch)
    if ch:
        lucky_sends_sent += 1
    time.sleep(10)
