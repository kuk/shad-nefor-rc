
from datetime import (
    datetime as Datetime,
    timedelta as Timedelta
)


START_DATE = Datetime.fromisoformat('2022-09-26')
START_DATE -= Timedelta(days=START_DATE.weekday())  # monday


def week_index(datetime):
    return (datetime - START_DATE).days // 7


def week_index_monday(index):
    return START_DATE + Timedelta(days=7 * index)


class Schedule:
    now = Datetime.utcnow

    def current_week_index(self):
        return week_index(self.now())

    def next_week_monday(self):
        return week_index_monday(self.current_week_index() + 1)
