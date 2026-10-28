"""Reference rules that decide the correct answers (standard library only).

Every answer in the benchmark is computed here, so anyone can re-check it.
Scope is kept narrow on purpose:
- Japanese eras: Showa, Heisei, Reiwa (1926-12-25 onward)
- National holidays: years 2022-2030 under the current Act on National Holidays
  (the dataset itself only uses 2025-2026, which are cross-checked in tests
  against the officially announced lists)
- Corporate Number (法人番号) check digit, as defined by the National Tax Agency
- Character width normalization via Unicode NFKC
"""
from __future__ import annotations

import datetime as _dt
import unicodedata

D = _dt.date

ERAS = [
    # (kanji, romaji, first day)
    ("令和", "Reiwa", D(2019, 5, 1)),
    ("平成", "Heisei", D(1989, 1, 8)),
    ("昭和", "Showa", D(1926, 12, 25)),
]


def to_wareki(d: D) -> str:
    """2019-05-01 -> '令和元年5月1日'."""
    for kanji, _r, start in ERAS:
        if d >= start:
            y = d.year - start.year + 1
            ys = "元" if y == 1 else str(y)
            return f"{kanji}{ys}年{d.month}月{d.day}日"
    raise ValueError("dates before 1926-12-25 are out of scope")


def from_wareki(era: str, year: int, month: int, day: int) -> D:
    """('平成', 31, 4, 30) -> 2019-04-30. Raises ValueError if the date is not in that era."""
    idx = [e[0] for e in ERAS].index(era)
    start = ERAS[idx][2]
    d = D(start.year + year - 1, month, day)
    end = ERAS[idx - 1][2] if idx > 0 else None
    if d < start or (end and d >= end):
        raise ValueError(f"{era}{year}年{month}月{day}日 does not exist")
    return d


# ---------------------------------------------------------------- holidays
HOLIDAY_YEARS = range(2022, 2031)


def _nth_monday(y: int, m: int, n: int) -> D:
    d = D(y, m, 1)
    offset = (0 - d.weekday()) % 7
    return d + _dt.timedelta(days=offset + 7 * (n - 1))


def _spring_equinox_day(y: int) -> int:
    return int(20.8431 + 0.242194 * (y - 1980) - int((y - 1980) / 4))


def _autumn_equinox_day(y: int) -> int:
    return int(23.2488 + 0.242194 * (y - 1980) - int((y - 1980) / 4))


def national_holidays(y: int) -> dict[D, str]:
    """All holidays (祝日 + 振替休日 + 国民の休日) for one year, with Japanese names."""
    if y not in HOLIDAY_YEARS:
        raise ValueError(f"holiday rules are only provided for {HOLIDAY_YEARS.start}-{HOLIDAY_YEARS.stop - 1}")
    h: dict[D, str] = {
        D(y, 1, 1): "元日",
        _nth_monday(y, 1, 2): "成人の日",
        D(y, 2, 11): "建国記念の日",
        D(y, 2, 23): "天皇誕生日",
        D(y, 3, _spring_equinox_day(y)): "春分の日",
        D(y, 4, 29): "昭和の日",
        D(y, 5, 3): "憲法記念日",
        D(y, 5, 4): "みどりの日",
        D(y, 5, 5): "こどもの日",
        _nth_monday(y, 7, 3): "海の日",
        D(y, 8, 11): "山の日",
        _nth_monday(y, 9, 3): "敬老の日",
        D(y, 9, _autumn_equinox_day(y)): "秋分の日",
        _nth_monday(y, 10, 2): "スポーツの日",
        D(y, 11, 3): "文化の日",
        D(y, 11, 23): "勤労感謝の日",
    }
    base = dict(h)
    # 国民の休日: a weekday sandwiched between two 祝日
    for d in sorted(base):
        nxt = d + _dt.timedelta(days=2)
        mid = d + _dt.timedelta(days=1)
        if nxt in base and mid not in base and mid.weekday() != 6:
            h[mid] = "国民の休日"
    # 振替休日: a 祝日 on Sunday moves to the next day that is not a holiday
    for d in sorted(base):
        if d.weekday() == 6:
            sub = d + _dt.timedelta(days=1)
            while sub in h:
                sub += _dt.timedelta(days=1)
            h[sub] = "振替休日"
    return dict(sorted(h.items()))


def holiday_name(d: D) -> str | None:
    return national_holidays(d.year).get(d)


def is_business_day(d: D) -> bool:
    """Business day = Monday-Friday and not a national holiday (year-end closures not included)."""
    return d.weekday() < 5 and holiday_name(d) is None


def add_business_days(d: D, n: int) -> D:
    """The n-th business day after d (d itself is not counted)."""
    if n < 1:
        raise ValueError("n must be >= 1")
    cur = d
    while n:
        cur += _dt.timedelta(days=1)
        if is_business_day(cur):
            n -= 1
    return cur


# ---------------------------------------------------------- corporate number
def corporate_check_digit(base12: str) -> int:
    """Check digit for a 12-digit base (National Tax Agency spec)."""
    if len(base12) != 12 or not base12.isdigit():
        raise ValueError("base must be 12 digits")
    s = sum(int(c) * (1 if i % 2 == 1 else 2) for i, c in enumerate(reversed(base12), 1))
    return 9 - s % 9


def is_valid_corporate_number(num: str) -> bool:
    """13 digits, first digit is the check digit. Accepts an invoice 'T' prefix."""
    if num.startswith("T"):
        num = num[1:]
    if len(num) != 13 or not num.isdigit():
        return False
    return int(num[0]) == corporate_check_digit(num[1:])


# ------------------------------------------------------------------- width
def normalize_width(s: str) -> str:
    """Full-width ASCII -> half-width, half-width katakana -> full-width (Unicode NFKC)."""
    return unicodedata.normalize("NFKC", s)
