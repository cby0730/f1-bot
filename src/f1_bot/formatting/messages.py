from datetime import datetime
from zoneinfo import ZoneInfo

from f1_bot.formatting.emoji import flag_icon, pos_icon, session_icon
from f1_bot.formatting.timezone import combine_race_dt, format_dt
from f1_bot.formatting.timezone import format_countdown as _countdown_str
from f1_bot.models.constructor import ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.models.race import Race
from f1_bot.models.results import (
    LapTime,
    PitStop,
    QualifyingResult,
    RaceResult,
    SessionResult,
    SprintResult,
)
from f1_bot.utils.sessions import SessionEntry


def _esc(text: str) -> str:
    """Escape legacy Markdown special characters: _ * ` ["""
    for ch in r"_*`[":
        text = text.replace(ch, f"\\{ch}")
    return text


# ---------- Next race / schedule ----------


def format_next_race(race: Race, user_tz: str) -> str:
    race_dt = combine_race_dt(race.date, race.time)
    lines = [
        f"🏁 *Next Race: {_esc(race.name)}*",
        f"📍 {race.circuit.name}, {race.circuit.locality}, {race.circuit.country}",
        "",
        f"🗓 *Race:* {format_dt(race_dt, user_tz)}",
        f"⏱ *Countdown:* {_countdown_str(race_dt)}",
    ]
    sessions = []
    _session_rows = [
        (race.fp1, "fp1", "FP1"),
        (race.fp2, "fp2", "FP2"),
        (race.fp3, "fp3", "FP3"),
        (race.sprint_qualifying, "sprint_qualifying", "Sprint Quali"),
        (race.sprint, "sprint", "Sprint"),
        (race.qualifying, "qualifying", "Quali"),
    ]
    for sess, key, label in _session_rows:
        if sess and sess.date is not None:
            dt = combine_race_dt(sess.date, sess.time)
            sessions.append(f"  {session_icon(key)} {label}: {format_dt(dt, user_tz)}")
        elif sess:
            sessions.append(f"  {session_icon(key)} {label}: TBD")
    if sessions:
        lines += ["", "*Sessions:*"] + sessions
    lines += ["", f"🏎 Round {race.round} of the {race.season} season"]
    return "\n".join(lines)


def format_schedule(races: list[Race], user_tz: str) -> str:
    today = datetime.now(ZoneInfo(user_tz)).date()
    lines = [f"📅 *{races[0].season if races else ''} F1 Season Calendar*\n"]
    for race in races:
        race_dt = combine_race_dt(race.date, race.time)
        past = race.date < today
        marker = "✅" if past else ("🔜" if race.date == today else "  ")
        lines.append(
            f"{marker} *R{race.round:02d}* {_esc(race.name)}\n       {format_dt(race_dt, user_tz)}"
        )
    return "\n".join(lines)


def format_countdown_msg(race: Race, user_tz: str) -> str:
    race_dt = combine_race_dt(race.date, race.time)
    return (
        f"⏱ *{_esc(race.name)}*\n"
        f"Countdown: *{_countdown_str(race_dt)}*\n"
        f"Race: {format_dt(race_dt, user_tz)}"
    )


def format_next_session(entry: SessionEntry, user_tz: str) -> str:
    dt = entry.starts_at
    time_str = format_dt(dt, user_tz) if dt else "TBD"
    countdown = _countdown_str(dt) if dt else "TBD"
    return "\n".join(
        [
            f"{session_icon(entry.key)} *Next {entry.label}: {_esc(entry.race.name)}*",
            f"📍 {entry.race.circuit.name}, {entry.race.circuit.locality}, {entry.race.circuit.country}",
            "",
            f"🗓 *{entry.label}:* {time_str}",
            f"⏱ *Countdown:* {countdown}",
            "",
            f"🏎 Round {entry.race.round} of the {entry.race.season} season",
        ]
    )


# ---------- Standings ----------


def format_driver_standings(standings: list[DriverStanding], season: int) -> str:
    lines = [f"🏆 *{season} Driver Standings (WDC)*\n"]
    for s in standings[:20]:
        icon = pos_icon(s.position)
        flag = flag_icon(s.driver.nationality or "")
        name = f"{s.driver.given_name} {s.driver.family_name}"
        lines.append(f"{icon} {flag} {name} — *{s.points:.0f} pts* ({s.constructor_name})")
    return "\n".join(lines)


def format_constructor_standings(standings: list[ConstructorStanding], season: int) -> str:
    lines = [f"🏭 *{season} Constructor Standings (WCC)*\n"]
    for s in standings[:10]:
        icon = pos_icon(s.position)
        flag = flag_icon(s.constructor.nationality or "")
        lines.append(f"{icon} {flag} {s.constructor.name} — *{s.points:.0f} pts*")
    return "\n".join(lines)


# ---------- Results ----------


def format_race_results(race: Race, results: list[RaceResult], top_n: int | None = None) -> str:
    lines = [f"🏁 *{_esc(race.name)} — Race Result*\n"]
    for r in results[:top_n] if top_n is not None else results[:20]:
        icon = pos_icon(r.position)
        flag = flag_icon(r.driver.nationality or "")
        name = f"{r.driver.given_name} {r.driver.family_name}"
        num_suffix = f" (#{r.driver.permanent_number})" if r.driver.permanent_number else ""
        fl = " ⚡" if r.fastest_lap_rank == 1 else ""

        time_str = r.time or r.status
        if time_str:
            if r.position == 1 and not time_str.startswith("+"):
                time_str = f"⏱ {time_str}"

        lines.append(f"{icon} {flag} {name}{num_suffix}{fl} — {time_str}")
    return "\n".join(lines)


def format_qualifying_results(
    race: Race, results: list[QualifyingResult], top_n: int | None = None
) -> str:
    lines = [f"⏱ *{_esc(race.name)} — Qualifying*\n"]
    for r in results[:top_n] if top_n is not None else results:
        icon = pos_icon(r.position)
        flag = flag_icon(r.driver.nationality or "")
        name = f"{r.driver.given_name} {r.driver.family_name}"
        best = r.q3 or r.q2 or r.q1 or "—"
        num_prefix = f" #{r.driver.permanent_number}" if r.driver.permanent_number else ""
        lines.append(f"{icon} {flag}{num_prefix} {name} — {best}")
    return "\n".join(lines)


def format_sprint_results(race: Race, results: list[SprintResult], top_n: int | None = None) -> str:
    lines = [f"💨 *{_esc(race.name)} — Sprint*\n"]
    for r in results[:top_n] if top_n is not None else results:
        icon = pos_icon(r.position)
        flag = flag_icon(r.driver.nationality or "")
        name = f"{r.driver.given_name} {r.driver.family_name}"
        num_prefix = f" #{r.driver.permanent_number}" if r.driver.permanent_number else ""
        lines.append(f"{icon} {flag}{num_prefix} {name} — {r.time or r.status}")
    return "\n".join(lines)


def format_session_results(
    entry: SessionEntry,
    results: list[SessionResult],
    drivers: dict[str | int, Driver] | None = None,
    top_n: int | None = None,
) -> str:
    lines = [f"{session_icon(entry.key)} *{_esc(entry.race.name)} — {entry.label} Result*\n"]
    sorted_results = sorted(results, key=lambda r: r.position or 99)
    for result in sorted_results[:top_n] if top_n is not None else sorted_results:
        pos = pos_icon(result.position) if result.position else "—"
        status = _format_session_result_status(result)
        driver_name = ""
        flag = "🏴"
        d = None
        if drivers:
            if result.driver_id and result.driver_id in drivers:
                d = drivers[result.driver_id]
            elif result.driver_number in drivers:
                d = drivers[result.driver_number]

        if d:
            driver_name = f" {d.given_name} {d.family_name}"
            flag = flag_icon(d.nationality or "")

        lines.append(f"{pos} {flag} #{result.driver_number}{driver_name} — {status}")
    return "\n".join(lines)


def _format_session_result_status(result: SessionResult) -> str:
    if result.dsq:
        return "DSQ"
    if result.dns:
        return "DNS"
    if result.dnf:
        return "DNF"
    duration = _format_result_value(result.duration)
    gap = _format_result_value(result.gap_to_leader)
    if duration and gap:
        return f"{duration} ({gap})"
    return duration or gap or "—"


def _format_result_value(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        parts = [_format_result_value(item) for item in value]
        parts = [part for part in parts if part]
        return " / ".join(parts) if parts else None
    return str(value)


# ---------- Pit stops ----------


def format_pitstops(race: Race | None, stops: list[PitStop], round_num: int) -> str:
    title = _esc(race.name) if race else f"Round {round_num}"
    lines = [f"🔧 *{title} — Pit Stops*\n"]
    # Group by driver: show each stop as a row
    by_driver: dict[str, list[PitStop]] = {}
    for s in stops:
        by_driver.setdefault(s.driver_id, []).append(s)
    for driver_id, driver_stops in sorted(by_driver.items()):
        stop_strs = []
        for s in sorted(driver_stops, key=lambda x: x.stop_number):
            dur = f"{s.duration:.1f}s" if s.duration else "—"
            stop_strs.append(f"Lap {s.lap}: {dur}")
        lines.append(f"🏎 *{_esc(driver_id)}*: {' | '.join(stop_strs)}")
    return "\n".join(lines)


# ---------- Laps ----------

_LAPS_PAGE_SIZE = 20


def _parse_lap_time_ms(time_str: str | None) -> int | None:
    """Convert 'M:SS.mmm' to milliseconds for comparison."""
    if not time_str:
        return None
    try:
        parts = time_str.split(":")
        if len(parts) == 2:
            mins = int(parts[0])
            secs = float(parts[1])
            return int((mins * 60 + secs) * 1000)
        return int(float(time_str) * 1000)
    except (ValueError, IndexError):
        return None


def format_laps_summary(
    race: Race | None, laps: list[LapTime], drivers: dict[int, Driver] | None = None
) -> str:
    """Per-driver best lap time and average — the default laps view."""
    title = _esc(race.name) if race else "Race"
    lines = [f"⏱ *{title} — Lap Times Summary*\n"]

    by_driver: dict[str, list[LapTime]] = {}
    for lap in laps:
        by_driver.setdefault(lap.driver_id, []).append(lap)

    rows = []
    for driver_id, driver_laps in sorted(by_driver.items()):
        times_ms = []
        for lap in driver_laps:
            if lap.time:
                ms = _parse_lap_time_ms(lap.time)
            elif lap.lap_duration is not None:
                ms = int(lap.lap_duration * 1000)
            else:
                ms = None
            times_ms.append(ms)

        valid = [t for t in times_ms if t is not None]
        if not valid:
            continue
        best_ms = min(valid)
        avg_ms = sum(valid) // len(valid)

        def ms_to_str(ms: int) -> str:
            m, rem = divmod(ms, 60000)
            s = rem / 1000
            return f"{m}:{s:06.3f}"

        rows.append((driver_id, ms_to_str(best_ms), ms_to_str(avg_ms), len(driver_laps), best_ms))

    rows.sort(key=lambda r: r[4])
    for driver_id, best, avg, count, _ in rows:
        label = driver_id
        try:
            num = int(driver_id)
            if drivers and num in drivers:
                d = drivers[num]
                label = d.code or d.family_name
        except ValueError:
            pass

        lines.append(f"🏎 *{_esc(label)}*: Best `{best}` | Avg `{avg}` | {count} laps")
    return "\n".join(lines)


def _fmt_sector(val: float | None) -> str:
    """Format a sector time as compact seconds with 1 decimal."""
    if val is None:
        return "  — "
    return f"{val:5.1f}"


def _fmt_lap_duration(val: float | None, time_str: str | None) -> str:
    """Format lap duration: prefer string form, fall back to float."""
    if time_str:
        return time_str
    if val is not None:
        m, s = divmod(val, 60)
        return f"{int(m)}:{s:06.3f}"
    return "—"


def format_laps_by_lap(
    race: Race | None,
    laps: list[LapTime],
    lap_number: int,
    total_laps: int,
    drivers: dict[int, Driver] | None = None,
) -> str:
    """All drivers' times for a single lap number, with sector times."""
    title = _esc(race.name) if race else "Race"
    lines = [f"⏱ *{title} — Lap {lap_number}/{total_laps}*\n"]

    lap_entries = [lap for lap in laps if lap.lap_number == lap_number]

    # Handle timing anomalies: append placeholder rows for active drivers who are missing data
    driver_max_lap = {}
    driver_min_lap = {}
    for lap in laps:
        d_id = lap.driver_id
        driver_max_lap[d_id] = max(driver_max_lap.get(d_id, 0), lap.lap_number)
        driver_min_lap[d_id] = min(driver_min_lap.get(d_id, 999), lap.lap_number)

    existing_drivers = {e.driver_id for e in lap_entries}
    for d_id in sorted(driver_max_lap.keys()):
        if driver_min_lap[d_id] <= lap_number <= driver_max_lap[d_id]:
            if d_id not in existing_drivers:
                lap_entries.append(
                    LapTime(
                        lap_number=lap_number,
                        driver_id=d_id,
                        position=None,
                        time=None,
                        duration_sector_1=None,
                        duration_sector_2=None,
                        duration_sector_3=None,
                        lap_duration=None,
                    )
                )

    lap_entries.sort(key=lambda x: (x.position or 999, x.driver_id))

    has_sectors = any(e.duration_sector_1 is not None for e in lap_entries)
    if has_sectors:
        lines.append("`     Driver  S1   │ S2   │ S3   │ Lap     `")
        for entry in lap_entries:
            pos = f"P{entry.position}" if entry.position else " —"
            s1 = _fmt_sector(entry.duration_sector_1)
            s2 = _fmt_sector(entry.duration_sector_2)
            s3 = _fmt_sector(entry.duration_sector_3)
            lap_t = _fmt_lap_duration(entry.lap_duration, entry.time)

            label = entry.driver_id
            try:
                num = int(entry.driver_id)
                if drivers and num in drivers:
                    label = drivers[num].code or entry.driver_id
            except ValueError:
                pass

            lines.append(f"`{pos:>3} {label:<4} {s1}│{s2}│{s3}│{lap_t}`")
    else:
        for entry in lap_entries:
            pos = f"P{entry.position}" if entry.position else "—"
            time_str = _fmt_lap_duration(entry.lap_duration, entry.time)

            label = entry.driver_id
            try:
                num = int(entry.driver_id)
                if drivers and num in drivers:
                    label = drivers[num].code or entry.driver_id
            except ValueError:
                pass

            lines.append(f"`{pos:>4}`  {_esc(label):<6} `{time_str}`")

    if not lap_entries:
        lines.append("_No data for this lap_")

    if lap_number == 1:
        lines.append("\n*Note: Lap 1 is the standing start lap; timing data may be incomplete.*")
    else:
        lines.append("\n*Note: Timing data from live feeds may occasionally be incomplete.*")

    return "\n".join(lines)


def format_laps_by_driver(
    race: Race | None,
    laps: list[LapTime],
    driver_id: str,
    page: int,
    drivers: dict[int, Driver] | None = None,
) -> str:
    """One driver's lap times, paginated, with sector times."""
    title = _esc(race.name) if race else "Race"
    driver_laps = sorted(
        [lap for lap in laps if lap.driver_id == driver_id], key=lambda x: x.lap_number
    )
    total = len(driver_laps)
    start = page * _LAPS_PAGE_SIZE
    end = start + _LAPS_PAGE_SIZE
    page_laps = driver_laps[start:end]

    label = driver_id
    try:
        num = int(driver_id)
        if drivers and num in drivers:
            d = drivers[num]
            label = f"{d.full_name} ({d.code})" if d.code else d.full_name
    except ValueError:
        pass

    lines = [f"⏱ *{title} — {_esc(label)} Lap Times*\n"]

    has_sectors = any(e.duration_sector_1 is not None for e in page_laps)
    if has_sectors:
        lines.append("`Lap   S1   │ S2   │ S3   │ Lap     `")
        for lap in page_laps:
            s1 = _fmt_sector(lap.duration_sector_1)
            s2 = _fmt_sector(lap.duration_sector_2)
            s3 = _fmt_sector(lap.duration_sector_3)
            lap_t = _fmt_lap_duration(lap.lap_duration, lap.time)
            lines.append(f"`L{lap.lap_number:>2}  {s1}│{s2}│{s3}│{lap_t}`")
    else:
        for lap in page_laps:
            time_str = _fmt_lap_duration(lap.lap_duration, lap.time)
            lines.append(f"Lap {lap.lap_number:>3}: `{time_str}`")

    if total > _LAPS_PAGE_SIZE:
        pages = (total + _LAPS_PAGE_SIZE - 1) // _LAPS_PAGE_SIZE
        lines.append(f"\n_Page {page + 1}/{pages} — {total} laps total_")
    lines.append("\n*Note: Timing data from live feeds may occasionally be incomplete.*")
    return "\n".join(lines)


def format_laps_driver_picker(race: Race | None) -> str:
    """Header text for the driver selection page."""
    title = _esc(race.name) if race else "Race"
    return f"⏱ *{title} — Select a Driver*\n\nTap a driver code to view their lap times:"


# ---------- Driver / Circuit ----------


def format_driver_profile(driver, standing=None) -> str:
    from f1_bot.formatting.emoji import flag_icon

    flag = flag_icon(driver.nationality or "")
    number = f"#{driver.permanent_number}" if driver.permanent_number else ""
    code = f" ({driver.code})" if driver.code else ""
    team = driver.team_name or (standing.constructor_name if standing else None) or "—"
    dob = driver.date_of_birth or "—"
    lines = [
        f"🏎 *{_esc(driver.full_name)}*{_esc(code)}  {flag}",
        f"Number: *{number}*  |  Team: *{_esc(team)}*",
        f"Nationality: {driver.nationality or '—'}  |  DOB: {dob}",
    ]
    if standing:
        lines.append(
            f"\n📊 *{standing.position}th* in WDC — *{standing.points:.0f} pts* ({standing.wins} wins)"
        )
    if driver.url:
        lines.append(f"\n[Wikipedia]({driver.url})")
    return "\n".join(lines)


def format_circuit_info(circuit, recent_races: list | None = None) -> str:
    from f1_bot.formatting.emoji import flag_icon

    flag = flag_icon(circuit.country)
    coord_str = ""
    if circuit.lat and circuit.lng:
        coord_str = f"\n📍 {circuit.lat:.4f}, {circuit.lng:.4f}"
    lines = [
        f"🏁 *{_esc(circuit.name)}*  {flag}",
        f"{circuit.locality}, {circuit.country}{coord_str}",
    ]
    if recent_races:
        lines.append("\n*Recent winners:*")
        for race in recent_races[:5]:
            lines.append(f"  {race.season}: {_esc(race.name)}")
    if circuit.url:
        lines.append(f"\n[Wikipedia]({circuit.url})")
    return "\n".join(lines)


# ---------- Utilities ----------


def no_data_message(what: str = "data") -> str:
    return f"⚠️ No {what} available yet. Try again after the next refresh."
