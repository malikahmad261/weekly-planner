"""Dates, working days and plain-language date parsing.

Everything is in the planner's local time zone (config/settings.json), stored
as naive ISO strings: dates as YYYY-MM-DD, timestamps as YYYY-MM-DDTHH:MM.
"""

import os
import re
from datetime import date, datetime, timedelta, timezone

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def _tz(name):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        # Asia/Karachi has no DST, so a fixed offset is a safe fallback when tzdata is missing.
        return timezone(timedelta(hours=5))


def now(tz_name="Asia/Karachi"):
    """Current local time, naive. PLANNER_NOW overrides it (tests, dry runs)."""
    forced = os.environ.get("PLANNER_NOW")
    if forced:
        return datetime.fromisoformat(forced).replace(tzinfo=None)
    return datetime.now(_tz(tz_name)).replace(tzinfo=None, second=0, microsecond=0)


def stamp(dt):
    return dt.isoformat(timespec="minutes")


def to_date(value):
    if value is None or isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(value[:10])


def fmt(d):
    """'Wed 28 Oct'."""
    d = to_date(d)
    return d.strftime("%a %-d %b") if d else "—"


class Calendar:
    """Working-day arithmetic. Weekends and holidays are skipped."""

    def __init__(self, working_days=("mon", "tue", "wed", "thu", "fri"), holidays=()):
        self.working = {WEEKDAYS.index(d[:3].lower()) for d in working_days}
        self.holidays = {to_date(h if isinstance(h, str) else h["date"]) for h in holidays}

    def is_working(self, d):
        return d.weekday() in self.working and d not in self.holidays

    def add(self, d, n):
        """n working days after d (n may be negative). add(d, 0) is d itself."""
        step = 1 if n >= 0 else -1
        remaining = abs(n)
        while remaining:
            d += timedelta(days=step)
            if self.is_working(d):
                remaining -= 1
        return d

    def next_working(self, d, include_today=False):
        if include_today and self.is_working(d):
            return d
        return self.add(d, 1)

    def between(self, a, b):
        """Working days in (a, b]. 0 if b <= a."""
        a, b = to_date(a), to_date(b)
        count = 0
        while a < b:
            a += timedelta(days=1)
            if self.is_working(a):
                count += 1
        return count

    def week_days(self, monday):
        return [monday + timedelta(days=i) for i in range(7) if self.is_working(monday + timedelta(days=i))]


def monday_of(d):
    return d - timedelta(days=d.weekday())


def week_id(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def week_monday(wid):
    y, w = wid.split("-W")
    return date.fromisocalendar(int(y), int(w), 1)


def resolve_week(expr, today):
    """'this' | 'next' | 'last' | '2026-W44' | a date inside the week -> week id."""
    expr = (expr or "this").strip().lower()
    if expr == "this":
        return week_id(today)
    if expr == "next":
        return week_id(today + timedelta(days=7))
    if expr == "last":
        return week_id(today - timedelta(days=7))
    if re.fullmatch(r"\d{4}-w\d{2}", expr):
        return expr.upper()
    return week_id(parse(expr, today))


def _weekday_index(word):
    word = word.lower()
    for i, name in enumerate(WEEKDAYS):
        if word.startswith(name) and len(word) >= 3:
            return i
    return None


def _month_index(word):
    word = word.lower()[:3]
    return MONTHS.index(word) + 1 if word in MONTHS else None


def parse(expr, today, cal=None):
    """Plain-language date -> date.

    Accepts: 2026-10-28, today, tomorrow, yesterday, wed (next one after
    today), this wed, next wed (in next week), eow / end of week, next week,
    end of next week, eom / end of month, in 3 days, in 2 working days, +3,
    +2wd, 28 oct, oct 28, 28/10.
    """
    cal = cal or Calendar()
    s = " ".join(str(expr).strip().lower().replace(",", " ").split())
    if not s:
        raise ValueError("empty date")
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    if s in ("today", "tod"):
        return today
    if s in ("tomorrow", "tmrw", "tmr"):
        return today + timedelta(days=1)
    if s == "yesterday":
        return today - timedelta(days=1)

    m = re.fullmatch(r"(?:in )?\+?(\d+) ?(d|day|days|wd|working days?|business days?)?", s)
    if m and (s.startswith("+") or s.startswith("in ")):
        n, unit = int(m.group(1)), m.group(2) or "d"
        if unit.startswith(("wd", "working", "business")):
            return cal.add(today, n)
        return today + timedelta(days=n)

    week_end = lambda monday: [d for d in cal.week_days(monday)][-1]
    if s in ("eow", "end of week", "end of the week", "this week", "by end of week", "end of this week"):
        d = week_end(monday_of(today))
        return d if d >= today else week_end(monday_of(today) + timedelta(days=7))
    if s == "next week":
        return cal.week_days(monday_of(today) + timedelta(days=7))[0]
    if s in ("end of next week", "eonw"):
        return week_end(monday_of(today) + timedelta(days=7))
    if s in ("eom", "end of month", "end of the month"):
        first_next = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        d = first_next - timedelta(days=1)
        while not cal.is_working(d):
            d -= timedelta(days=1)
        return d

    parts = s.split()
    if len(parts) == 2 and parts[0] in ("this", "next") and _weekday_index(parts[1]) is not None:
        wd = _weekday_index(parts[1])
        monday = monday_of(today) + timedelta(days=7 if parts[0] == "next" else 0)
        return monday + timedelta(days=wd)
    if len(parts) == 1 and _weekday_index(parts[0]) is not None:
        wd = _weekday_index(parts[0])
        ahead = (wd - today.weekday()) % 7 or 7
        return today + timedelta(days=ahead)

    day = month = None
    m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)? ([a-z]+)", s)
    if m and _month_index(m.group(2)):
        day, month = int(m.group(1)), _month_index(m.group(2))
    m = re.fullmatch(r"([a-z]+) (\d{1,2})(?:st|nd|rd|th)?", s)
    if m and _month_index(m.group(1)):
        day, month = int(m.group(2)), _month_index(m.group(1))
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", s)
    if m:  # day/month, as written in Pakistan
        day, month = int(m.group(1)), int(m.group(2))
    if day and month:
        d = date(today.year, month, day)
        if d < today - timedelta(days=7):
            d = date(today.year + 1, month, day)
        return d
    raise ValueError(f"can't read date: {expr!r}")
