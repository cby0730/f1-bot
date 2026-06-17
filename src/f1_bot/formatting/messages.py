from datetime import date

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
    today = date.today()
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


def format_race_results(race: Race, results: list[RaceResult]) -> str:
    lines = [f"🏁 *{_esc(race.name)} — Race Result*\n"]
    for r in results[:20]:
        icon = pos_icon(r.position)
        flag = flag_icon(r.driver.nationality or "")
        name = f"{r.driver.given_name} {r.driver.family_name}"
        time_str = r.time or r.status
        fl = " ⚡" if r.fastest_lap_rank == 1 else ""
        lines.append(f"{icon} {flag} {name}{fl} — {time_str}")
    return "\n".join(lines)


def format_qualifying_results(race: Race, results: list[QualifyingResult]) -> str:
    lines = [f"⏱ *{_esc(race.name)} — Qualifying*\n"]
    for r in results:
        icon = pos_icon(r.position)
        flag = flag_icon(r.driver.nationality or "")
        name = f"{r.driver.given_name} {r.driver.family_name}"
        best = r.q3 or r.q2 or r.q1 or "—"
        lines.append(f"{icon} {flag} {name} — {best}")
    return "\n".join(lines)


def format_sprint_results(race: Race, results: list[SprintResult]) -> str:
    lines = [f"💨 *{_esc(race.name)} — Sprint*\n"]
    for r in results:
        icon = pos_icon(r.position)
        flag = flag_icon(r.driver.nationality or "")
        name = f"{r.driver.given_name} {r.driver.family_name}"
        lines.append(f"{icon} {flag} {name} — {r.time or r.status}")
    return "\n".join(lines)


def format_session_results(
    entry: SessionEntry, results: list[SessionResult], drivers: dict[int, Driver] | None = None
) -> str:
    lines = [f"{session_icon(entry.key)} *{_esc(entry.race.name)} — {entry.label} Result*\n"]
    for result in sorted(results, key=lambda r: r.position or 99):
        pos = pos_icon(result.position) if result.position else "—"
        status = _format_session_result_status(result)
        driver_name = ""
        if drivers and result.driver_number in drivers:
            d = drivers[result.driver_number]
            driver_name = f" {d.given_name} {d.family_name}"
        lines.append(f"{pos} #{result.driver_number}{driver_name} — {status}")
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


def format_laps(race: Race | None, laps: list[LapTime], round_num: int) -> str:
    title = _esc(race.name) if race else f"Round {round_num}"
    lines = [f"⏱ *{title} — Lap Times (sample)*\n"]
    # Show first 20 lap entries — full lap data can be huge
    for lap in laps[:20]:
        time_str = lap.time or "—"
        pos = f"P{lap.position}" if lap.position else "—"
        lines.append(f"Lap {lap.lap_number:>2}  {pos:>4}  {_esc(lap.driver_id):<20} {time_str}")
    if len(laps) > 20:
        lines.append(f"\n_…and {len(laps) - 20} more laps_")
    return "\n".join(lines)


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
            lines.append(f"  {race.season}: {race.name}")
    if circuit.url:
        lines.append(f"\n[Wikipedia]({circuit.url})")
    return "\n".join(lines)


# ---------- Utilities ----------


def no_data_message(what: str = "data") -> str:
    return f"⚠️ No {what} available yet. Try again after the next refresh."
