from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from f1_bot.formatting.i18n import DEFAULT_LANG, t


def is_valid_timezone(tz_name: str) -> bool:
    try:
        ZoneInfo(tz_name)
        return True
    except (ZoneInfoNotFoundError, KeyError):
        return False


def localize(dt: datetime, tz_name: str) -> datetime:
    """Convert a UTC datetime to the given timezone."""
    tz = ZoneInfo(tz_name)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(tz)


def combine_race_dt(race_date: date, race_time: time | None) -> datetime:
    """Combine a race date + optional time (assumed UTC) into a datetime."""
    if race_time is None:
        return datetime(race_date.year, race_date.month, race_date.day, tzinfo=UTC)
    return datetime.combine(race_date, race_time, tzinfo=UTC)


def format_dt(dt: datetime, tz_name: str, lang: str = DEFAULT_LANG) -> str:
    """Format a UTC datetime in the target timezone and language.

    Weekday and month names come from the catalog, not ``strftime``: ``%a``/``%b``
    read the *process-global* C locale, which is shared across all users and
    unsafe to mutate from async handlers. Only the numeric parts use ``strftime``.
    """
    local = localize(dt, tz_name)
    stamp = t(
        "datetime.date_time",
        lang,
        weekday=t(f"datetime.weekday_short.{local.weekday()}", lang),
        month=t(f"datetime.month_short.{local.month}", lang),
        day=local.day,
        day2=f"{local.day:02d}",
        time=local.strftime("%H:%M"),
    )
    return f"{stamp} {local.tzname()}"


def format_countdown(target: datetime, lang: str = DEFAULT_LANG) -> str:
    """Return a human-readable countdown from now to target (UTC)."""
    now = datetime.now(tz=UTC)
    if target.tzinfo is None:
        target = target.replace(tzinfo=UTC)
    delta = target - now
    if delta.total_seconds() <= 0:
        return t("datetime.countdown_finished", lang)
    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    parts = []
    if days:
        parts.append(t("datetime.unit_day", lang, n=days))
    if hours:
        parts.append(t("datetime.unit_hour", lang, n=hours))
    if minutes and not days:
        parts.append(t("datetime.unit_minute", lang, n=minutes))
    return " ".join(parts) or t("datetime.countdown_lt_minute", lang)


def region_label(region: str, lang: str) -> str:
    """Display name for a `TIMEZONE_REGIONS` slug."""
    return t(f"settings.region_{region}", lang)


# Common timezones grouped by region for the inline keyboard.
# Keys are stable slugs, not display text: they travel inside `tz:region:{slug}`
# callback_data, which must not change when the label is translated.
TIMEZONE_REGIONS: dict[str, list[tuple[str, str]]] = {
    "asia": [
        ("Taipei / Beijing", "Asia/Taipei"),
        ("Tokyo", "Asia/Tokyo"),
        ("Seoul", "Asia/Seoul"),
        ("Bangkok", "Asia/Bangkok"),
        ("Singapore", "Asia/Singapore"),
        ("Mumbai", "Asia/Kolkata"),
        ("Dubai", "Asia/Dubai"),
    ],
    "europe": [
        ("London", "Europe/London"),
        ("Paris / Berlin", "Europe/Paris"),
        ("Rome / Madrid", "Europe/Rome"),
        ("Amsterdam", "Europe/Amsterdam"),
        ("Moscow", "Europe/Moscow"),
    ],
    "americas": [
        ("New York", "America/New_York"),
        ("Chicago", "America/Chicago"),
        ("Denver", "America/Denver"),
        ("Los Angeles", "America/Los_Angeles"),
        ("São Paulo", "America/Sao_Paulo"),
        ("Mexico City", "America/Mexico_City"),
    ],
    "other": [
        ("UTC", "UTC"),
        ("Sydney", "Australia/Sydney"),
        ("Auckland", "Pacific/Auckland"),
    ],
}
