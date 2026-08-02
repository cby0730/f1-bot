from datetime import datetime
from unicodedata import east_asian_width
from zoneinfo import ZoneInfo

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.emoji import flag_icon, pos_icon, session_icon
from f1_bot.formatting.i18n import DEFAULT_LANG, t
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
from f1_bot.utils.championship import (
    WCC_RACE_MAX,
    WCC_SPRINT_MAX,
    WDC_RACE_MAX,
    WDC_SPRINT_MAX,
    ClinchStatus,
    clinch_status,
    max_remaining_points,
)
from f1_bot.utils.sessions import SessionEntry, session_label, session_short_label


def _esc(text: str) -> str:
    """Escape legacy Markdown special characters: _ * ` ["""
    for ch in r"_*`[":
        text = text.replace(ch, f"\\{ch}")
    return text


def _display_width(s: str) -> int:
    """Terminal columns `s` occupies in a monospace font.

    East-Asian Wide/Fullwidth glyphs render at 2× the Latin advance. Ambiguous ("A")
    chars — the `─` separator among them — count as 1: `─` appears identically on
    every row, so it shifts all rows equally and cannot break cross-row alignment.
    """
    return sum(2 if east_asian_width(c) in ("W", "F") else 1 for c in s)


def _pad_display(s: str, width: int) -> str:
    """Left-align `s` to `width` *display* columns.

    `f"{s:<10}"` pads to code points, which under-pads CJK by exactly one space per
    glyph and drifts every translated row out of alignment.
    """
    return s + " " * max(0, width - _display_width(s))


# ---------- Next race / schedule ----------


def format_next_race(race: Race, ctx: RenderContext) -> str:
    race_dt = combine_race_dt(race.date, race.time)
    lines = [
        t("schedule.next_race_header", ctx.lang, name=_esc(race.name)),
        t(
            "schedule.location",
            ctx.lang,
            circuit=_esc(race.circuit.name),
            locality=_esc(race.circuit.locality),
            country=_esc(race.circuit.country),
        ),
        "",
        t("schedule.race_line", ctx.lang, time=format_dt(race_dt, ctx.tz, ctx.lang)),
        t("schedule.countdown_line", ctx.lang, countdown=_countdown_str(race_dt, ctx.lang)),
    ]
    sessions = []
    _session_rows = [
        (race.fp1, "fp1"),
        (race.fp2, "fp2"),
        (race.fp3, "fp3"),
        (race.sprint_qualifying, "sprint_qualifying"),
        (race.sprint, "sprint"),
        (race.qualifying, "qualifying"),
    ]
    for sess, key in _session_rows:
        if not sess:
            continue
        if sess.date is not None:
            dt = combine_race_dt(sess.date, sess.time)
            when = format_dt(dt, ctx.tz, ctx.lang)
        else:
            when = t("common.tbd", ctx.lang)
        sessions.append(
            t(
                "schedule.session_row",
                ctx.lang,
                icon=session_icon(key),
                label=session_short_label(key, ctx.lang),
                time=when,
            )
        )
    if sessions:
        lines += ["", t("schedule.sessions_header", ctx.lang)] + sessions
    lines += ["", t("common.round_of_season", ctx.lang, round=race.round, season=race.season)]
    return "\n".join(lines)


def format_schedule(races: list[Race], ctx: RenderContext) -> str:
    today = datetime.now(ZoneInfo(ctx.tz)).date()
    season = races[0].season if races else ""
    lines = [t("schedule.calendar_header", ctx.lang, season=season) + "\n"]
    for race in races:
        race_dt = combine_race_dt(race.date, race.time)
        past = race.date < today
        marker = "✅" if past else ("🔜" if race.date == today else "  ")
        lines.append(
            t(
                "schedule.calendar_row",
                ctx.lang,
                marker=marker,
                round=f"{race.round:02d}",
                name=_esc(race.name),
                time=format_dt(race_dt, ctx.tz, ctx.lang),
            )
        )
    return "\n".join(lines)


def format_countdown_msg(race: Race, ctx: RenderContext) -> str:
    race_dt = combine_race_dt(race.date, race.time)
    return t(
        "schedule.countdown_msg",
        ctx.lang,
        name=_esc(race.name),
        countdown=_countdown_str(race_dt, ctx.lang),
        time=format_dt(race_dt, ctx.tz, ctx.lang),
    )


def format_next_session(entry: SessionEntry, ctx: RenderContext) -> str:
    dt = entry.starts_at
    label = session_label(entry.key, ctx.lang)
    tbd = t("common.tbd", ctx.lang)
    time_str = format_dt(dt, ctx.tz, ctx.lang) if dt else tbd
    countdown = _countdown_str(dt, ctx.lang) if dt else tbd
    return "\n".join(
        [
            t(
                "schedule.next_session_header",
                ctx.lang,
                icon=session_icon(entry.key),
                label=label,
                name=_esc(entry.race.name),
            ),
            t(
                "schedule.location",
                ctx.lang,
                circuit=_esc(entry.race.circuit.name),
                locality=_esc(entry.race.circuit.locality),
                country=_esc(entry.race.circuit.country),
            ),
            "",
            t("schedule.next_session_time", ctx.lang, label=label, time=time_str),
            t("schedule.countdown_line", ctx.lang, countdown=countdown),
            "",
            t(
                "common.round_of_season",
                ctx.lang,
                round=entry.race.round,
                season=entry.race.season,
            ),
        ]
    )


# ---------- Standings ----------


def format_driver_standings(
    standings: list[DriverStanding], season: int, ctx: RenderContext
) -> str:
    lines = [t("standings.wdc_header", ctx.lang, season=season) + "\n"]
    for s in standings[:20]:
        lines.append(
            t(
                "standings.driver_row",
                ctx.lang,
                icon=pos_icon(s.position),
                flag=flag_icon(s.driver.nationality or ""),
                name=_esc(f"{s.driver.given_name} {s.driver.family_name}"),
                points=f"{s.points:.0f}",
                team=_esc(s.constructor_name),
            )
        )
    return "\n".join(lines)


def format_constructor_standings(
    standings: list[ConstructorStanding], season: int, ctx: RenderContext
) -> str:
    lines = [t("standings.wcc_header", ctx.lang, season=season) + "\n"]
    for s in standings[:10]:
        lines.append(
            t(
                "standings.constructor_row",
                ctx.lang,
                icon=pos_icon(s.position),
                flag=flag_icon(s.constructor.nationality or ""),
                name=_esc(s.constructor.name),
                points=f"{s.points:.0f}",
            )
        )
    return "\n".join(lines)


# ---------- Title clinch analysis (/title) ----------


def _remaining_line(remaining_races: int, remaining_sprints: int, lang: str) -> str:
    """'N races + M sprints left' — always shows both counts.

    English plural words are resolved here and passed in; zh-Hant's template simply
    ignores them, since Chinese has no plural inflection.
    """
    return t(
        "title.remaining",
        lang,
        races=remaining_races,
        races_word=t("title.word_race" if remaining_races == 1 else "title.word_races", lang),
        sprints=remaining_sprints,
        sprints_word=t(
            "title.word_sprint" if remaining_sprints == 1 else "title.word_sprints", lang
        ),
    )


def _format_title(
    standings: list,
    remaining_races: int,
    remaining_sprints: int,
    season: int,
    ctx: RenderContext,
    *,
    header_icon: str,
    kind: str,
    race_max: int,
    sprint_max: int,
    name_of,
    champion_key: str,
) -> str:
    """Shared clinch-analysis body for WDC and WCC — layout only.

    All math comes from ``championship``. ``name_of`` maps a standing to its display
    name; the two views differ only in that, the icons, and the point constants.
    """
    if not standings:
        return no_data_message("common.noun_standings", ctx)

    ranked = sorted(standings, key=lambda s: s.position)
    leader = ranked[0]
    max_remaining = max_remaining_points(remaining_races, remaining_sprints, race_max, sprint_max)

    lines = [
        t("title.header", ctx.lang, icon=header_icon, season=season, kind=kind) + "\n",
        _remaining_line(remaining_races, remaining_sprints, ctx.lang),
        t("title.max_points", ctx.lang, points=max_remaining),
        "",
    ]

    # Clinch verdict: leader vs. the single strongest chaser (index [1]). A lone
    # competitor (no chaser) is trivially uncatchable → clinched.
    if len(ranked) < 2:
        status = ClinchStatus(clinched=True, magic_number=None)
    else:
        status = clinch_status(leader.points, ranked[1].points, max_remaining)

    if status.clinched:
        lines.append(
            t(
                "title.clinched",
                ctx.lang,
                name=_esc(name_of(leader)),
                season=season,
                champion=t(champion_key, ctx.lang),
            )
        )
        lines.append("")

    for s in ranked[:3]:
        icon = pos_icon(s.position)
        name = _esc(name_of(s))
        if s.position == leader.position:
            lines.append(
                t("title.leader_row", ctx.lang, icon=icon, name=name, points=f"{s.points:.0f}")
            )
        else:
            deficit = leader.points - s.points
            lines.append(
                t(
                    "title.chaser_row",
                    ctx.lang,
                    icon=icon,
                    name=name,
                    points=f"{s.points:.0f}",
                    deficit=f"{deficit:.0f}",
                )
            )

    if not status.clinched:
        lines.append("")
        lines.append(
            t("title.magic_number", ctx.lang, name=_esc(name_of(leader)), n=status.magic_number)
        )

    return "\n".join(lines)


def format_title_wdc(
    standings: list[DriverStanding],
    remaining_races: int,
    remaining_sprints: int,
    season: int,
    ctx: RenderContext,
) -> str:
    return _format_title(
        standings,
        remaining_races,
        remaining_sprints,
        season,
        ctx,
        header_icon="🏆",
        kind="WDC",
        race_max=WDC_RACE_MAX,
        sprint_max=WDC_SPRINT_MAX,
        name_of=lambda s: f"{s.driver.given_name} {s.driver.family_name}",
        champion_key="title.champion_wdc",
    )


def format_title_wcc(
    standings: list[ConstructorStanding],
    remaining_races: int,
    remaining_sprints: int,
    season: int,
    ctx: RenderContext,
) -> str:
    return _format_title(
        standings,
        remaining_races,
        remaining_sprints,
        season,
        ctx,
        header_icon="🏭",
        kind="WCC",
        race_max=WCC_RACE_MAX,
        sprint_max=WCC_SPRINT_MAX,
        name_of=lambda s: s.constructor.name,
        champion_key="title.champion_wcc",
    )


# ---------- Results ----------


def _result_row(ctx: RenderContext, icon: str, flag: str, name: str, extra: str, value: str) -> str:
    # `name` is API free text (driver names); escape here so every caller is covered.
    return t(
        "results.row", ctx.lang, icon=icon, flag=flag, name=_esc(name), extra=extra, value=value
    )


def format_race_results(
    race: Race, results: list[RaceResult], ctx: RenderContext, top_n: int | None = None
) -> str:
    lines = [t("results.race_header", ctx.lang, name=_esc(race.name)) + "\n"]
    for r in results[:top_n] if top_n is not None else results[:20]:
        name = f"{r.driver.given_name} {r.driver.family_name}"
        num_suffix = f" (#{r.driver.permanent_number})" if r.driver.permanent_number else ""
        fl = " ⚡" if r.fastest_lap_rank == 1 else ""

        time_str = r.time or r.status
        if time_str and r.position == 1 and not time_str.startswith("+"):
            time_str = f"⏱ {time_str}"

        lines.append(
            _result_row(
                ctx,
                pos_icon(r.position),
                flag_icon(r.driver.nationality or ""),
                name,
                f"{num_suffix}{fl}",
                time_str,
            )
        )
    return "\n".join(lines)


def format_qualifying_results(
    race: Race, results: list[QualifyingResult], ctx: RenderContext, top_n: int | None = None
) -> str:
    lines = [t("results.qualifying_header", ctx.lang, name=_esc(race.name)) + "\n"]
    for r in results[:top_n] if top_n is not None else results:
        name = f"{r.driver.given_name} {r.driver.family_name}"
        best = r.q3 or r.q2 or r.q1 or "—"
        num_prefix = f" #{r.driver.permanent_number}" if r.driver.permanent_number else ""
        lines.append(
            _result_row(
                ctx,
                pos_icon(r.position),
                f"{flag_icon(r.driver.nationality or '')}{num_prefix}",
                name,
                "",
                best,
            )
        )
    return "\n".join(lines)


def format_sprint_results(
    race: Race, results: list[SprintResult], ctx: RenderContext, top_n: int | None = None
) -> str:
    lines = [t("results.sprint_header", ctx.lang, name=_esc(race.name)) + "\n"]
    for r in results[:top_n] if top_n is not None else results:
        name = f"{r.driver.given_name} {r.driver.family_name}"
        num_prefix = f" #{r.driver.permanent_number}" if r.driver.permanent_number else ""
        lines.append(
            _result_row(
                ctx,
                pos_icon(r.position),
                f"{flag_icon(r.driver.nationality or '')}{num_prefix}",
                name,
                "",
                r.time or r.status,
            )
        )
    return "\n".join(lines)


def format_session_results(
    entry: SessionEntry,
    results: list[SessionResult],
    ctx: RenderContext,
    drivers: dict[str | int, Driver] | None = None,
    top_n: int | None = None,
) -> str:
    lines = [
        t(
            "results.session_header",
            ctx.lang,
            icon=session_icon(entry.key),
            name=_esc(entry.race.name),
            label=session_label(entry.key, ctx.lang),
        )
        + "\n"
    ]
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

        lines.append(_result_row(ctx, pos, flag, f"#{result.driver_number}{driver_name}", "", status))
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


def format_pitstops(
    race: Race | None, stops: list[PitStop], round_num: int, ctx: RenderContext
) -> str:
    title = _esc(race.name) if race else t("common.round_short", ctx.lang, round=round_num)
    lines = [t("race_data.pitstops_header", ctx.lang, title=title) + "\n"]
    # Group by driver: show each stop as a row
    by_driver: dict[str, list[PitStop]] = {}
    for s in stops:
        by_driver.setdefault(s.driver_id, []).append(s)
    for driver_id, driver_stops in sorted(by_driver.items()):
        stop_strs = []
        for s in sorted(driver_stops, key=lambda x: x.stop_number):
            dur = f"{s.duration:.1f}s" if s.duration else "—"
            stop_strs.append(t("race_data.pitstop_lap", ctx.lang, lap=s.lap, duration=dur))
        lines.append(
            t(
                "race_data.pitstop_row",
                ctx.lang,
                driver=_esc(driver_id),
                stops=" | ".join(stop_strs),
            )
        )
    return "\n".join(lines)


# ---------- Laps ----------

_LAPS_PAGE_SIZE = 20


def _resolve_driver_label(driver_id: str, drivers: dict[int, Driver] | None) -> str:
    """Resolve a driver_id to a short display label (code or family name)."""
    try:
        num = int(driver_id)
        if drivers and num in drivers:
            d = drivers[num]
            return d.code or d.family_name
    except ValueError:
        pass
    return driver_id


def _ms_to_str(ms: int) -> str:
    m, rem = divmod(ms, 60000)
    s = rem / 1000
    return f"{m}:{s:06.3f}"


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
    race: Race | None,
    laps: list[LapTime],
    ctx: RenderContext,
    drivers: dict[int, Driver] | None = None,
) -> str:
    """Per-driver best lap time and average — the default laps view."""
    title = _esc(race.name) if race else t("common.race_fallback_title", ctx.lang)
    lines = [t("race_data.laps_summary_header", ctx.lang, title=title) + "\n"]

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

        valid = [t_ms for t_ms in times_ms if t_ms is not None]
        if not valid:
            continue
        best_ms = min(valid)
        avg_ms = sum(valid) // len(valid)

        rows.append((driver_id, _ms_to_str(best_ms), _ms_to_str(avg_ms), len(driver_laps), best_ms))

    rows.sort(key=lambda r: r[4])
    for driver_id, best, avg, count, _ in rows:
        label = _resolve_driver_label(driver_id, drivers)
        lines.append(
            t(
                "race_data.laps_summary_row",
                ctx.lang,
                label=_esc(label),
                best=best,
                avg=avg,
                count=count,
            )
        )
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
    ctx: RenderContext,
    drivers: dict[int, Driver] | None = None,
) -> str:
    """All drivers' times for a single lap number, with sector times."""
    title = _esc(race.name) if race else t("common.race_fallback_title", ctx.lang)
    lines = [
        t("race_data.lap_header", ctx.lang, title=title, lap=lap_number, total=total_laps) + "\n"
    ]

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
        lines.append(t("race_data.lap_table_header", ctx.lang))
        for entry in lap_entries:
            pos = f"P{entry.position}" if entry.position else " —"
            s1 = _fmt_sector(entry.duration_sector_1)
            s2 = _fmt_sector(entry.duration_sector_2)
            s3 = _fmt_sector(entry.duration_sector_3)
            lap_t = _fmt_lap_duration(entry.lap_duration, entry.time)

            label = _resolve_driver_label(entry.driver_id, drivers)

            lines.append(f"`{pos:>3} {label:<4} {s1}│{s2}│{s3}│{lap_t}`")
    else:
        for entry in lap_entries:
            pos = f"P{entry.position}" if entry.position else "—"
            time_str = _fmt_lap_duration(entry.lap_duration, entry.time)

            label = _resolve_driver_label(entry.driver_id, drivers)

            lines.append(f"`{pos:>4}`  {_esc(label):<6} `{time_str}`")

    if not lap_entries:
        lines.append(t("race_data.no_lap_entries", ctx.lang))

    if lap_number == 1:
        lines.append(t("race_data.note_lap1", ctx.lang))
    else:
        lines.append(t("race_data.note_timing", ctx.lang))

    return "\n".join(lines)


def format_laps_by_driver(
    race: Race | None,
    laps: list[LapTime],
    driver_id: str,
    page: int,
    ctx: RenderContext,
    drivers: dict[int, Driver] | None = None,
) -> str:
    """One driver's lap times, paginated, with sector times."""
    title = _esc(race.name) if race else t("common.race_fallback_title", ctx.lang)
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

    lines = [
        t("race_data.driver_laps_header", ctx.lang, title=title, label=_esc(label)) + "\n"
    ]

    has_sectors = any(e.duration_sector_1 is not None for e in page_laps)
    if has_sectors:
        lines.append(t("race_data.driver_table_header", ctx.lang))
        for lap in page_laps:
            s1 = _fmt_sector(lap.duration_sector_1)
            s2 = _fmt_sector(lap.duration_sector_2)
            s3 = _fmt_sector(lap.duration_sector_3)
            lap_t = _fmt_lap_duration(lap.lap_duration, lap.time)
            lines.append(f"`L{lap.lap_number:>2}  {s1}│{s2}│{s3}│{lap_t}`")
    else:
        for lap in page_laps:
            time_str = _fmt_lap_duration(lap.lap_duration, lap.time)
            lines.append(
                t(
                    "race_data.driver_lap_row",
                    ctx.lang,
                    lap=f"{lap.lap_number:>3}",
                    time=time_str,
                )
            )

    if total > _LAPS_PAGE_SIZE:
        pages = (total + _LAPS_PAGE_SIZE - 1) // _LAPS_PAGE_SIZE
        lines.append(
            t("race_data.page_footer", ctx.lang, page=page + 1, pages=pages, total=total)
        )
    lines.append(t("race_data.note_timing", ctx.lang))
    return "\n".join(lines)


def format_laps_driver_picker(race: Race | None, ctx: RenderContext) -> str:
    """Header text for the driver selection page."""
    title = _esc(race.name) if race else t("common.race_fallback_title", ctx.lang)
    return t("race_data.driver_picker_header", ctx.lang, title=title)


# ---------- Driver / Circuit ----------


def format_driver_profile(driver, standing, ctx: RenderContext) -> str:
    flag = flag_icon(driver.nationality or "")
    number = f"#{driver.permanent_number}" if driver.permanent_number else ""
    code = f" ({driver.code})" if driver.code else ""
    team = driver.team_name or (standing.constructor_name if standing else None) or "—"
    dob = driver.date_of_birth or "—"
    lines = [
        t(
            "extras.profile_header",
            ctx.lang,
            name=_esc(driver.full_name),
            code=_esc(code),
            flag=flag,
        ),
        t("extras.profile_number_team", ctx.lang, number=number, team=_esc(team)),
        t(
            "extras.profile_nationality_dob",
            ctx.lang,
            nationality=_esc(driver.nationality or "—"),
            dob=dob,
        ),
    ]
    if standing:
        lines.append(
            t(
                "extras.profile_standing",
                ctx.lang,
                position=standing.position,
                points=f"{standing.points:.0f}",
                wins=standing.wins,
            )
        )
    if driver.url:
        safe_url = driver.url.replace("(", "%28").replace(")", "%29")
        lines.append(t("extras.wikipedia", ctx.lang, url=safe_url))
    return "\n".join(lines)


def format_circuit_info(circuit, recent_races: list | None, ctx: RenderContext) -> str:
    from f1_bot.formatting.emoji import circuit_flag_icon

    flag = circuit_flag_icon(circuit.country)
    coord_str = ""
    if circuit.lat and circuit.lng:
        coord_str = t(
            "extras.circuit_coords", ctx.lang, lat=f"{circuit.lat:.4f}", lng=f"{circuit.lng:.4f}"
        )
    lines = [
        t("extras.circuit_header", ctx.lang, name=_esc(circuit.name), flag=flag),
        t(
            "extras.circuit_location",
            ctx.lang,
            locality=_esc(circuit.locality),
            country=_esc(circuit.country),
            coords=coord_str,
        ),
    ]
    if recent_races:
        lines.append(t("extras.recent_winners", ctx.lang))
        for race in recent_races[:5]:
            lines.append(
                t("extras.recent_row", ctx.lang, season=race.season, name=_esc(race.name))
            )
    if circuit.url:
        safe_url = circuit.url.replace("(", "%28").replace(")", "%29")
        lines.append(t("extras.wikipedia", ctx.lang, url=safe_url))
    return "\n".join(lines)


# ---------- Utilities ----------


def no_data_message(what_key: str = "common.noun_data", ctx: RenderContext | None = None, **kwargs):
    """'No <thing> available yet' — with `<thing>` itself translated.

    `what_key` is a catalog key, not a word: splicing a raw English noun into a
    Chinese sentence is the leak this signature exists to prevent.
    """
    lang = ctx.lang if ctx else DEFAULT_LANG
    return t("common.no_data", lang, what=t(what_key, lang, **kwargs))


# ---------- Compare ----------

# Display-width target for the left label column of the /compare grid. Sized off the
# widest shipped label across both languages (`Quali H2H` = 9, `正賽+衝刺` = 9) plus a
# minimum gap; asserted in tests so a longer future label fails loudly.
_CMP_LABEL_WIDTH = 12


def _cmp_row(label: str, a_str: str, b_str: str, extra: str = "") -> str:
    """One aligned comparison row (rendered inside a monospace code block)."""
    return f"{_pad_display(label, _CMP_LABEL_WIDTH)}{a_str:>3} ─ {b_str:>3}{extra}"


# (row label key, stats key) for the int-pair rows, rendered in order below Points.
_CMP_STAT_ROWS = (
    ("compare.row_quali", "quali"),
    ("compare.row_race", "race"),
    ("compare.row_wins", "wins"),
    ("compare.row_podiums", "podiums"),
    ("compare.row_dnfs", "dnfs"),
)


def format_driver_comparison(a: Driver, b: Driver, stats: dict, ctx: RenderContext) -> str:
    """Render a two-column, race+sprint-combined head-to-head of two drivers.

    ``stats`` carries pre-aggregated (a, b) tuples for each row. ``points`` values
    may be ``None`` when a driver is absent from the standings (mid-season data lag).
    When ``stats["has_data"]`` is falsy, the table is replaced by the empty-data
    message — never a misleading 0–0 table.
    """
    header = t("compare.header", ctx.lang, a=_esc(a.family_name), b=_esc(b.family_name))
    if not stats.get("has_data"):
        return f"{header}\n\n{t('compare.no_data', ctx.lang)}"

    pa, pb = stats["points"]

    def _pt(p: float | None) -> str:
        return "—" if p is None else f"{p:.0f}"

    pa_str, pb_str = _pt(pa), _pt(pb)
    gap = f"   (+{abs(pa - pb):.0f})" if pa is not None and pb is not None else ""

    rows = [_cmp_row(t("compare.row_points", ctx.lang), pa_str, pb_str, gap)]
    rows += [
        _cmp_row(t(label_key, ctx.lang), str(stats[key][0]), str(stats[key][1]))
        for label_key, key in _CMP_STAT_ROWS
    ]
    table = "\n".join(rows)
    footnote = _esc(t("compare.footnote", ctx.lang))
    return f"{header}\n\n```\n{table}\n```\n{footnote}"


# ---------- Notifications ----------


def format_notification_message(
    race: "Race | None", session_key: str, minutes_before: int, lang: str = DEFAULT_LANG
) -> str:
    """Format the push notification message sent to users.

    Takes a bare `lang`, not a RenderContext: it renders no clock time, so there is
    no timezone to resolve and no reason to make the background sender pay for one.
    """
    label = _esc(session_label(session_key, lang))
    if race:
        return t(
            "notifications.push_with_race",
            lang,
            name=_esc(race.name),
            session=label,
            minutes=minutes_before,
        )
    return t("notifications.push_no_race", lang, session=label, minutes=minutes_before)
