"""Date, time and countdown vocabulary.

Weekday and month names live here rather than coming from ``strftime`` because
``strftime`` reads the *process-global* C locale — not per-user, and not safe to
mutate from async request handlers.

``datetime.date_time`` receives both ``day`` (unpadded) and ``day2`` (zero-padded):
English uses ``{day2}`` to reproduce ``%d`` byte-for-byte, Chinese uses ``{day}``
because a leading zero reads wrong in ``7月30日``.
"""

DATETIME: dict[str, dict[str, str]] = {
    # Monday = 0, matching datetime.date.weekday()
    "datetime.weekday_short.0": {"en": "Mon", "zh-Hant": "週一"},
    "datetime.weekday_short.1": {"en": "Tue", "zh-Hant": "週二"},
    "datetime.weekday_short.2": {"en": "Wed", "zh-Hant": "週三"},
    "datetime.weekday_short.3": {"en": "Thu", "zh-Hant": "週四"},
    "datetime.weekday_short.4": {"en": "Fri", "zh-Hant": "週五"},
    "datetime.weekday_short.5": {"en": "Sat", "zh-Hant": "週六"},
    "datetime.weekday_short.6": {"en": "Sun", "zh-Hant": "週日"},
    "datetime.month_short.1": {"en": "Jan", "zh-Hant": "1月"},
    "datetime.month_short.2": {"en": "Feb", "zh-Hant": "2月"},
    "datetime.month_short.3": {"en": "Mar", "zh-Hant": "3月"},
    "datetime.month_short.4": {"en": "Apr", "zh-Hant": "4月"},
    "datetime.month_short.5": {"en": "May", "zh-Hant": "5月"},
    "datetime.month_short.6": {"en": "Jun", "zh-Hant": "6月"},
    "datetime.month_short.7": {"en": "Jul", "zh-Hant": "7月"},
    "datetime.month_short.8": {"en": "Aug", "zh-Hant": "8月"},
    "datetime.month_short.9": {"en": "Sep", "zh-Hant": "9月"},
    "datetime.month_short.10": {"en": "Oct", "zh-Hant": "10月"},
    "datetime.month_short.11": {"en": "Nov", "zh-Hant": "11月"},
    "datetime.month_short.12": {"en": "Dec", "zh-Hant": "12月"},
    "datetime.date_time": {
        "en": "{weekday} {month} {day2}, {time}",
        "zh-Hant": "{month}{day}日 ({weekday}) {time}",
    },
    "datetime.countdown_finished": {
        "en": "In progress / finished",
        "zh-Hant": "進行中／已結束",
    },
    "datetime.countdown_lt_minute": {"en": "< 1 minute", "zh-Hant": "不到 1 分鐘"},
    "datetime.unit_day": {"en": "{n}d", "zh-Hant": "{n} 天"},
    "datetime.unit_hour": {"en": "{n}h", "zh-Hant": "{n} 小時"},
    "datetime.unit_minute": {"en": "{n}m", "zh-Hant": "{n} 分"},
}
