from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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


def format_dt(dt: datetime, tz_name: str, fmt: str = "%a %b %d, %H:%M") -> str:
    """Format a UTC datetime in the target timezone."""
    local = localize(dt, tz_name)
    return local.strftime(fmt) + f" {local.tzname()}"


def format_countdown(target: datetime) -> str:
    """Return a human-readable countdown from now to target (UTC)."""
    now = datetime.now(tz=UTC)
    if target.tzinfo is None:
        target = target.replace(tzinfo=UTC)
    delta = target - now
    if delta.total_seconds() <= 0:
        return "In progress / finished"
    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes and not days:
        parts.append(f"{minutes}m")
    return " ".join(parts) or "< 1 minute"


# Common timezones grouped by region for the inline keyboard
TIMEZONE_REGIONS: dict[str, list[tuple[str, str]]] = {
    "🌏 Asia": [
        ("Taipei / Beijing", "Asia/Taipei"),
        ("Tokyo", "Asia/Tokyo"),
        ("Seoul", "Asia/Seoul"),
        ("Bangkok", "Asia/Bangkok"),
        ("Singapore", "Asia/Singapore"),
        ("Mumbai", "Asia/Kolkata"),
        ("Dubai", "Asia/Dubai"),
    ],
    "🌍 Europe": [
        ("London", "Europe/London"),
        ("Paris / Berlin", "Europe/Paris"),
        ("Rome / Madrid", "Europe/Rome"),
        ("Amsterdam", "Europe/Amsterdam"),
        ("Moscow", "Europe/Moscow"),
    ],
    "🌎 Americas": [
        ("New York", "America/New_York"),
        ("Chicago", "America/Chicago"),
        ("Denver", "America/Denver"),
        ("Los Angeles", "America/Los_Angeles"),
        ("São Paulo", "America/Sao_Paulo"),
        ("Mexico City", "America/Mexico_City"),
    ],
    "🌐 UTC / Other": [
        ("UTC", "UTC"),
        ("Sydney", "Australia/Sydney"),
        ("Auckland", "Pacific/Auckland"),
    ],
}
