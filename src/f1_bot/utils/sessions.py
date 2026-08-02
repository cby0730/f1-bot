from dataclasses import dataclass
from datetime import UTC, date, datetime

from f1_bot.formatting.i18n import t
from f1_bot.formatting.timezone import combine_race_dt
from f1_bot.models.race import Race, RaceSession, Session

SESSION_ALIASES = {
    "fp1": "fp1",
    "practice1": "fp1",
    "firstpractice": "fp1",
    "fp2": "fp2",
    "practice2": "fp2",
    "secondpractice": "fp2",
    "fp3": "fp3",
    "practice3": "fp3",
    "thirdpractice": "fp3",
    "practice": "practice",
    "quali": "qualifying",
    "qualifying": "qualifying",
    "qualification": "qualifying",
    "sq": "sprint_qualifying",
    "sprintquali": "sprint_qualifying",
    "sprintqualifying": "sprint_qualifying",
    "sprintshootout": "sprint_qualifying",
    "sprint": "sprint",
    "race": "race",
}

SESSION_LABELS = {
    "fp1": "FP1",
    "fp2": "FP2",
    "fp3": "FP3",
    "sprint_qualifying": "Sprint Qualifying",
    "sprint": "Sprint",
    "qualifying": "Qualifying",
    "race": "Race",
}

def session_label(key: str, lang: str) -> str:
    """Display label for a session key, e.g. ``"qualifying"`` → ``"Qualifying"``.

    ``SESSION_LABELS`` above is retained as the *key set* (``find_next_sessions``
    membership-tests against it); only the display path goes through the catalog.
    Unknown keys echo back, matching the old ``SESSION_LABELS.get(k, k)`` behaviour.
    """
    try:
        return t(f"session.{key}", lang)
    except KeyError:
        return key


def session_short_label(key: str, lang: str) -> str:
    """Abbreviated label for the compact session list in ``/next``.

    Distinct from `session_label` because that list has always used ``Quali`` /
    ``Sprint Quali`` to fit the line — a second, narrower vocabulary, not a synonym.
    """
    try:
        return t(f"session.short.{key}", lang)
    except KeyError:
        return session_label(key, lang)


SESSION_GROUPS = {
    "all": {"fp1", "fp2", "fp3", "sprint_qualifying", "sprint", "qualifying", "race"},
    "practice": {"fp1", "fp2", "fp3"},
    "qualifying": {"qualifying", "sprint_qualifying"},
    "sprint": {"sprint", "sprint_qualifying"},
    "race": {"race"},
}


@dataclass(frozen=True)
class SessionEntry:
    race: Race
    key: str
    session: RaceSession
    starts_at: datetime | None


def normalize_session_key(value: str | None) -> str | None:
    if value is None:
        return None
    key = value.lower().replace(" ", "").replace("-", "").replace("_", "")
    return SESSION_ALIASES.get(key)


def session_entries(races: list[Race]) -> list[SessionEntry]:
    entries: list[SessionEntry] = []
    for race in races:
        rows = [
            ("fp1", race.fp1),
            ("fp2", race.fp2),
            ("fp3", race.fp3),
            ("sprint_qualifying", race.sprint_qualifying),
            ("sprint", race.sprint),
            ("qualifying", race.qualifying),
            ("race", RaceSession(name="Race", date=race.date, time=race.time)),
        ]
        for key, session in rows:
            if session is None:
                continue
            starts_at = combine_race_dt(session.date, session.time) if session.date else None
            entries.append(SessionEntry(race=race, key=key, session=session, starts_at=starts_at))
    return sorted(
        entries,
        key=lambda e: (e.starts_at is None, e.starts_at or datetime.max.replace(tzinfo=UTC)),
    )


def find_next_sessions(
    races: list[Race],
    group: str = "all",
    limit: int = 1,
    now: datetime | None = None,
) -> list[SessionEntry]:
    now = now or datetime.now(tz=UTC)
    if group in SESSION_GROUPS:
        allowed = SESSION_GROUPS[group]
    else:
        normalized = normalize_session_key(group)
        if normalized in SESSION_LABELS:
            allowed = {normalized}
        else:
            raise ValueError(f"Unknown session group or key: {group}")
    upcoming = [
        entry
        for entry in session_entries(races)
        if entry.key in allowed and entry.starts_at is not None and entry.starts_at >= now
    ]
    return upcoming[:limit]


def find_next_session(
    races: list[Race],
    group: str = "all",
    now: datetime | None = None,
) -> SessionEntry | None:
    res = find_next_sessions(races, group, limit=1, now=now)
    return res[0] if res else None


def find_recent_completed_sessions(
    races: list[Race],
    session_key: str | None = None,
    limit: int = 1,
    now: datetime | None = None,
) -> list[SessionEntry]:
    now = now or datetime.now(tz=UTC)
    normalized = normalize_session_key(session_key)
    if normalized is None and session_key is not None:
        return []
    completed = [
        entry
        for entry in session_entries(races)
        if entry.starts_at is not None
        and entry.starts_at <= now
        and (normalized is None or entry.key == normalized)
    ]
    return list(reversed(completed[-limit:])) if completed else []


def find_recent_completed_session(
    races: list[Race],
    session_key: str | None = None,
    now: datetime | None = None,
) -> SessionEntry | None:
    res = find_recent_completed_sessions(races, session_key, limit=1, now=now)
    return res[0] if res else None


def find_race_session(races: list[Race], round_num: int, session_key: str) -> SessionEntry | None:
    normalized = normalize_session_key(session_key)
    if normalized is None:
        return None
    race = next((r for r in races if r.round == round_num), None)
    if race is None:
        return None
    return next((e for e in session_entries([race]) if e.key == normalized), None)


def match_openf1_session(entry: SessionEntry, sessions: list[Session]) -> Session | None:
    if entry.starts_at is None:
        return None
    expected_date = entry.starts_at.date()
    candidates = [
        session
        for session in sessions
        if _session_date(session) == expected_date and _openf1_session_key(session) == entry.key
    ]
    return candidates[0] if candidates else None


def _session_date(session: Session) -> date | None:
    if not session.date_start:
        return None
    try:
        return datetime.fromisoformat(session.date_start.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _openf1_session_key(session: Session) -> str | None:
    normalized = normalize_session_key(session.session_name)
    if normalized is not None:
        return normalized
    return normalize_session_key(session.session_type)
