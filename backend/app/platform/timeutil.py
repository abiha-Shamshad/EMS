"""Company calendar: working days and hours in the company time zone; storage is always UTC (spec Section 10)."""
import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def valid_time_zone(name: str) -> bool:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


class Calendar:
    """Wraps organizations.time_zone + organizations.work_hours."""

    def __init__(self, time_zone: str, work_hours: dict):
        self.tz = ZoneInfo(time_zone)
        self.days = set(work_hours.get("days") or [])
        self.start = dt.time.fromisoformat(work_hours.get("start", "09:00"))
        self.end = dt.time.fromisoformat(work_hours.get("end", "18:00"))
        self.grace_minutes = int(work_hours.get("late_grace_minutes", 0))

    def local(self, at: dt.datetime) -> dt.datetime:
        return at.astimezone(self.tz)

    def local_date(self, at: dt.datetime | None = None) -> dt.date:
        return self.local(at or utcnow()).date()

    def is_working_day(self, day: dt.date) -> bool:
        return WEEKDAYS[day.weekday()] in self.days

    def at_local(self, day: dt.date, time: dt.time) -> dt.datetime:
        return dt.datetime.combine(day, time, tzinfo=self.tz).astimezone(dt.UTC)

    def work_start(self, day: dt.date) -> dt.datetime:
        return self.at_local(day, self.start)

    def work_end(self, day: dt.date) -> dt.datetime:
        return self.at_local(day, self.end)

    def day_bounds(self, day: dt.date) -> tuple[dt.datetime, dt.datetime]:
        """[start, end) of a company-local calendar day, in UTC."""
        start = dt.datetime.combine(day, dt.time.min, tzinfo=self.tz)
        end = dt.datetime.combine(day + dt.timedelta(days=1), dt.time.min, tzinfo=self.tz)
        return start.astimezone(dt.UTC), end.astimezone(dt.UTC)

    def minutes_late(self, started_at: dt.datetime) -> int:
        """max(0, check_in_local - (start + grace)) in whole minutes, on a working day only."""
        day = self.local_date(started_at)
        if not self.is_working_day(day):
            return 0
        threshold = self.work_start(day) + dt.timedelta(minutes=self.grace_minutes)
        return max(0, int((started_at - threshold).total_seconds() // 60))

    def working_days(self, start: dt.date, end: dt.date) -> int:
        if end < start:
            return 0
        return sum(1 for i in range((end - start).days + 1) if self.is_working_day(start + dt.timedelta(days=i)))
