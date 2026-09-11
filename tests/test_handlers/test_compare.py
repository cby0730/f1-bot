"""Tests for /compare — driver head-to-head.

Aggregation is pure Python over result dicts, so these tests use lightweight
AsyncMock repos (no dev PostgreSQL needed). Each test encodes *why* a behavior
matters, per spec 002's testing approach — not merely what the code does today.
"""

from unittest.mock import AsyncMock, MagicMock

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.messages import format_driver_comparison
from f1_bot.handlers.compare import (
    _aggregate,
    _compare_callback,
    _menu_keyboard,
    _real_drivers,
)
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.models.results import is_classified_finish

# --- Builders ---------------------------------------------------------------


def _driver(did: str, family: str, number: str | None = None) -> Driver:
    return Driver(
        driver_id=did,
        given_name=family,
        family_name=family,
        nationality="Dutch",
        permanent_number=number,
    )


def _result(did: str, position: int, status: str = "Finished") -> dict:
    """A race/sprint result dict as stored in JSONB (not a Pydantic model)."""
    return {"position": position, "status": status, "driver": {"driver_id": did}}


def _quali(did: str, position: int) -> dict:
    return {"position": position, "driver": {"driver_id": did}}


def _standing(did: str, family: str, points: float, position: int) -> DriverStanding:
    return DriverStanding(
        position=position,
        points=points,
        wins=0,
        driver=_driver(did, family),
        constructor_name="Red Bull",
    )


def _repo(
    *,
    last_round: int,
    race: dict | None = None,
    sprint: dict | None = None,
    quali: dict | None = None,
    standings: list | None = None,
    drivers_map: dict | None = None,
):
    """Build an AsyncMock repo. race/sprint/quali map {round_num: list[dict] | None}."""
    repo = MagicMock()
    repo.get_schedule_bounds = AsyncMock(return_value={"last_completed_round": last_round})
    repo.get_race_results = AsyncMock(side_effect=lambda s, r: (race or {}).get(r))
    repo.get_sprint_results = AsyncMock(side_effect=lambda s, r: (sprint or {}).get(r))
    repo.get_qualifying_results = AsyncMock(side_effect=lambda s, r: (quali or {}).get(r))
    repo.get_driver_standings = AsyncMock(return_value=standings or [])
    repo.get_drivers_map = AsyncMock(return_value=drivers_map or {})
    return repo


A, B = "max_verstappen", "norris"


# --- DNF classification -----------------------------------------------------


def test_dnf_whitelist_accident_is_dnf_lap_is_finished():
    """Whitelist rule: an unseen failure string must never read as a finish.

    'Accident' → DNF; '+1 Lap' and 2026's 'Lapped' (classified, a lap down) →
    finished. Guards against regressing the whitelist into a blacklist that
    would misclassify novel strings, and against treating Jolpica's 2026
    'Lapped' token as a retirement.
    """
    assert is_classified_finish("Finished") is True
    assert is_classified_finish("Lapped") is True  # 2026 Jolpica; not '+1 Lap'
    assert is_classified_finish("+1 Lap") is True
    assert is_classified_finish("+2 Laps") is True
    assert is_classified_finish("Accident") is False
    assert is_classified_finish("Engine") is False
    assert is_classified_finish("Retired") is False
    assert is_classified_finish("Did not start") is False


async def test_dnf_counted_in_aggregate():
    """A driver's DNF status feeds the DNFs row."""
    repo = _repo(last_round=1, race={1: [_result(A, 1), _result(B, 18, "Accident")]})
    stats = await _aggregate(repo, 2026, A, B)
    assert stats["dnfs"] == (0, 1)


async def test_lapped_is_not_counted_as_dnf_in_aggregate():
    """A classified lapped finish must not increment the DNFs row.

    WHY: same 2026 Jolpica 'Lapped' token that falsely DNF-tagged Hungarian GP laps.
    """
    repo = _repo(last_round=1, race={1: [_result(A, 1), _result(B, 8, "Lapped")]})
    stats = await _aggregate(repo, 2026, A, B)
    assert stats["dnfs"] == (0, 0)
    assert stats["race"] == (1, 0)


# --- Sprint inclusion -------------------------------------------------------


async def test_sprint_win_and_dnf_included():
    """Scope is race+sprint combined: a sprint win/DNF must show in Wins/DNFs.

    Proves the aggregation isn't silently race-only — the exact inconsistency the
    grill removed from the original draft.
    """
    repo = _repo(
        last_round=1,
        race={1: [_result(A, 3), _result(B, 2)]},
        sprint={1: [_result(A, 1), _result(B, 20, "Engine")]},
    )
    stats = await _aggregate(repo, 2026, A, B)
    assert stats["wins"] == (1, 0)  # A's sprint win
    assert stats["dnfs"] == (0, 1)  # B's sprint DNF


async def test_h2h_counts_per_session_not_per_round():
    """A weekend with both a race and a sprint can add 2 to the H2H tally, not 1."""
    repo = _repo(
        last_round=1,
        race={1: [_result(A, 1), _result(B, 2)]},
        sprint={1: [_result(A, 1), _result(B, 2)]},
    )
    stats = await _aggregate(repo, 2026, A, B)
    assert stats["race"] == (2, 0)  # A wins both the race and the sprint session


# --- H2H DNF handling -------------------------------------------------------


async def test_single_dnf_finisher_wins_h2h():
    """A finishes, B retires → A wins that session (finishing is part of the contest)."""
    repo = _repo(last_round=1, race={1: [_result(A, 12), _result(B, 20, "Gearbox")]})
    stats = await _aggregate(repo, 2026, A, B)
    assert stats["race"] == (1, 0)


async def test_both_dnf_excluded_from_h2h():
    """Both retire → session excluded; retirement order is not a competitive signal."""
    repo = _repo(
        last_round=1,
        race={1: [_result(A, 19, "Collision"), _result(B, 20, "Engine")]},
    )
    stats = await _aggregate(repo, 2026, A, B)
    assert stats["race"] == (0, 0)


async def test_h2h_skips_session_with_only_one_driver():
    """Only one driver contested the session → excluded from both tallies."""
    repo = _repo(last_round=1, race={1: [_result(A, 1)]})  # B absent
    stats = await _aggregate(repo, 2026, A, B)
    assert stats["race"] == (0, 0)


# --- Qualifying H2H (distinct gate, no DNF branch) --------------------------


async def test_quali_h2h_requires_both_present():
    """Quali gate: a round where only one driver qualified adds 0.

    Distinct from the race H2H rule — quali has no DNF fallback, so the 'both must
    have a result' gate is the *only* thing guarding it.
    """
    repo = _repo(
        last_round=2,
        quali={1: [_quali(A, 3), _quali(B, 5)], 2: [_quali(A, 1)]},  # round 2: B absent
    )
    stats = await _aggregate(repo, 2026, A, B)
    assert stats["quali"] == (1, 0)  # only round 1 counts; A out-qualified B


# --- Podium boundary --------------------------------------------------------


async def test_podium_boundary_pos3_counts_pos4_does_not():
    """Pins the `<= 3` edge so a `< 3` slip is caught."""
    repo = _repo(
        last_round=2,
        race={1: [_result(A, 3), _result(B, 4)], 2: [_result(A, 2), _result(B, 5)]},
    )
    stats = await _aggregate(repo, 2026, A, B)
    assert stats["podiums"] == (2, 0)  # A: P3 + P2; B: P4 + P5 → none


# --- Empty / partial data ---------------------------------------------------


async def test_empty_data_yields_message_not_zero_table():
    """Zero completed rounds and empty standings → has_data False (no 0–0 table)."""
    repo = _repo(last_round=0, standings=[])
    stats = await _aggregate(repo, 2026, A, B)
    assert stats["has_data"] is False


async def test_none_session_is_skipped():
    """A round whose results are None (not synced / no sprint) is stepped over.

    Proves the aggregator never iterates None — the partial-sync crash path.
    """
    repo = _repo(
        last_round=2,
        race={1: [_result(A, 1), _result(B, 2)], 2: None},  # round 2 unsynced
        sprint={1: None},  # no sprint that weekend
    )
    stats = await _aggregate(repo, 2026, A, B)
    assert stats["has_data"] is True
    assert stats["race"] == (1, 0)  # only round 1's race counted, no crash


async def test_missing_from_standings_shows_dash_but_still_computes():
    """A driver absent from standings → Points None (renders '—'), H2H still computes.

    The mid-season data-lag path, distinct from the whole-table empty case.
    """
    repo = _repo(
        last_round=1,
        race={1: [_result(A, 1), _result(B, 2)]},
        standings=[_standing(A, "Verstappen", 25.0, 1)],  # B missing
    )
    stats = await _aggregate(repo, 2026, A, B)
    assert stats["points"] == (25.0, None)
    assert stats["has_data"] is True
    assert stats["race"] == (1, 0)

    # And the formatter renders '—' for the absent driver's points.
    text = format_driver_comparison(
        _driver(A, "Verstappen"), _driver(B, "Norris"), stats, RenderContext()
    )
    assert "—" in text


async def test_points_gap_is_absolute_difference():
    """Gap equals |A.points − B.points| from standings."""
    stats = {
        "has_data": True,
        "points": (310.0, 241.0),
        "quali": (0, 0),
        "race": (0, 0),
        "wins": (0, 0),
        "podiums": (0, 0),
        "dnfs": (0, 0),
    }
    text = format_driver_comparison(
        _driver(A, "Verstappen"), _driver(B, "Norris"), stats, RenderContext()
    )
    assert "+69" in text


# --- Formatter conventions --------------------------------------------------


def test_formatter_escapes_markdown_special_chars():
    """A driver name with '_' is passed through _esc so legacy MARKDOWN doesn't break.

    Per the ParseMode convention: use a name with a special char, never a clean one.
    """
    stats = {
        "has_data": True,
        "points": (10.0, 5.0),
        "quali": (0, 0),
        "race": (0, 0),
        "wins": (0, 0),
        "podiums": (0, 0),
        "dnfs": (0, 0),
    }
    text = format_driver_comparison(
        _driver(A, "Mc_Laren"), _driver(B, "Norris"), stats, RenderContext()
    )
    assert r"Mc\_Laren" in text


def test_formatter_empty_data_has_no_table():
    """has_data False → the no-data message, never a 0–0 table."""
    stats = {"has_data": False}
    # Render in zh-Hant so the assertion pins the translated no-data message.
    text = format_driver_comparison(
        _driver(A, "Verstappen"), _driver(B, "Norris"), stats, RenderContext(lang="zh-Hant")
    )
    assert "尚無足夠比賽資料" in text
    assert "─" not in text  # no comparison rows


# --- Keyboard / UI invariants -----------------------------------------------


def test_step2_grid_excludes_driver_a():
    """A driver can't be compared to themselves — Step 2 omits driver A."""
    drivers = [_driver(A, "Verstappen"), _driver(B, "Norris")]
    kb = _menu_keyboard(drivers, exclude_id=A, a_id=A)
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert all(A not in d.split(":")[3:] for d in all_data)
    assert any(d == f"cmp:b:{A}:{B}" for d in all_data)


async def test_openf1_synthetic_ids_filtered():
    """Synthetic openf1_* ids never surface as buttons (only real drivers)."""
    drivers_map = {
        1: _driver(A, "Verstappen", "1"),
        4: _driver(B, "Norris", "4"),
        99: _driver("openf1_99_ghost", "Ghost", "99"),
    }
    repo = _repo(last_round=0, drivers_map=drivers_map)
    drivers = await _real_drivers(repo, 2026)
    ids = {d.driver_id for d in drivers}
    assert ids == {A, B}


def test_step2_callback_data_under_64_bytes():
    """The longest realistic driver pairing stays under Telegram's 64-byte cap."""
    drivers = [_driver("max_verstappen", "Verstappen"), _driver("antonelli", "Antonelli")]
    kb = _menu_keyboard(drivers, exclude_id="max_verstappen", a_id="max_verstappen")
    for row in kb.inline_keyboard:
        for btn in row:
            assert len(btn.callback_data.encode()) <= 64


# --- Callback guards & discipline -------------------------------------------


async def test_malformed_callback_answers_invalid_selection():
    """A spoofed/short cmp:b payload → 'Invalid selection', no crash."""
    query = AsyncMock()
    query.data = "cmp:b:only_a_id"  # missing b_id
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()
    ctx.bot_data = {"repo": MagicMock()}

    await _compare_callback(update, ctx)

    query.answer.assert_awaited_once()
    assert query.answer.await_args.kwargs.get("text") == "Invalid selection"


async def test_callback_answered_exactly_once_on_result():
    """query.answer() is called exactly once per invocation (PTB double-answer footgun)."""
    drivers_map = {1: _driver(A, "Verstappen", "1"), 4: _driver(B, "Norris", "4")}
    repo = _repo(
        last_round=1,
        race={1: [_result(A, 1), _result(B, 2)]},
        standings=[_standing(A, "Verstappen", 25.0, 1), _standing(B, "Norris", 18.0, 2)],
        drivers_map=drivers_map,
    )
    query = AsyncMock()
    query.data = f"cmp:b:{A}:{B}"
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()
    ctx.bot_data = {"repo": repo}

    await _compare_callback(update, ctx)

    query.answer.assert_awaited_once()


# --- Happy path (single end-to-end smoke) -----------------------------------


async def test_happy_path_step1_to_result():
    """cmp:a → cmp:b threads ids through Step 1 → Step 2 → a populated result table.

    One smoke test only; the intermediate invariants (A==B exclusion, openf1
    filtering) are covered separately above.
    """
    drivers_map = {1: _driver(A, "Verstappen", "1"), 4: _driver(B, "Norris", "4")}
    repo = _repo(
        last_round=1,
        race={1: [_result(A, 1), _result(B, 2)]},
        standings=[_standing(A, "Verstappen", 25.0, 1), _standing(B, "Norris", 18.0, 2)],
        drivers_map=drivers_map,
    )
    ctx = MagicMock()
    ctx.bot_data = {"repo": repo}

    # Step 1 → Step 2 (pick A)
    q1 = AsyncMock()
    q1.data = f"cmp:a:{A}"
    u1 = MagicMock()
    u1.callback_query = q1
    await _compare_callback(u1, ctx)
    step2_kb = q1.edit_message_text.await_args.kwargs["reply_markup"]
    step2_data = [b.callback_data for row in step2_kb.inline_keyboard for b in row]
    assert f"cmp:b:{A}:{B}" in step2_data  # B offered, A baked in

    # Step 2 → result (pick B)
    q2 = AsyncMock()
    q2.data = f"cmp:b:{A}:{B}"
    u2 = MagicMock()
    u2.callback_query = q2
    await _compare_callback(u2, ctx)
    text = q2.edit_message_text.await_args.kwargs["text"]
    assert "Verstappen" in text and "Norris" in text
    assert "Race+Spr" in text  # populated table, not the empty message
    result_kb = q2.edit_message_text.await_args.kwargs["reply_markup"]
    result_data = [b.callback_data for row in result_kb.inline_keyboard for b in row]
    assert f"cmp:a:{A}" in result_data
    assert f"drv:detail:{A}" in result_data
    assert "cmp:list" not in result_data
