"""Tests for the round picker callback handler."""

from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from telegram.constants import ParseMode
from telegram.error import BadRequest

from f1_bot.handlers.round_picker import _compute_navigable_rounds, _round_picker_callback
from f1_bot.models.race import Circuit, Race, RaceSession


def _circuit(country="UK"):
    return Circuit(circuit_id="test", name="Test", locality="Test", country=country)


def _past_date(days_ago: int) -> date:
    return date.today() - timedelta(days=days_ago)


def _future_date(days_ahead: int) -> date:
    return date.today() + timedelta(days=days_ahead)


def _completed_race(rnd: int, days_ago: int = 10, country: str = "UK") -> Race:
    return Race(
        season=2025,
        round=rnd,
        name=f"GP {rnd}",
        circuit=_circuit(country),
        date=_past_date(days_ago),
        time=time(14, 0),
        qualifying=RaceSession(name="Qualifying", date=_past_date(days_ago + 1), time=time(14, 0)),
    )


def _upcoming_race(rnd: int, days_ahead: int = 10, country: str = "UK") -> Race:
    return Race(
        season=2025,
        round=rnd,
        name=f"GP {rnd}",
        circuit=_circuit(country),
        date=_future_date(days_ahead),
        time=time(14, 0),
        fp1=RaceSession(name="FP1", date=_future_date(days_ahead - 2), time=time(10, 0)),
        qualifying=RaceSession(
            name="Qualifying", date=_future_date(days_ahead - 1), time=time(14, 0)
        ),
    )


def _mock_context(races, bounds):
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=bounds)
    ctx = MagicMock()
    ctx.bot_data = {"repo": repo}
    return ctx


def _mock_update(callback_data: str):
    update = MagicMock()
    update.callback_query = MagicMock()
    update.callback_query.data = callback_data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


# ---------------------------------------------------------------------------
# _compute_navigable_rounds
# ---------------------------------------------------------------------------


class TestComputeNavigableRounds:
    def test_pit_uses_completed_range(self):
        bounds = {"last_completed_round": 5}
        result = _compute_navigable_rounds("pit", [], bounds)
        assert result == [1, 2, 3, 4, 5]

    def test_lap_uses_completed_range(self):
        bounds = {"last_completed_round": 3}
        result = _compute_navigable_rounds("lap", [], bounds)
        assert result == [1, 2, 3]

    def test_pit_no_completed(self):
        bounds = {"last_completed_round": None}
        result = _compute_navigable_rounds("pit", [], bounds)
        assert result == []

    @patch("f1_bot.handlers.round_picker.upcoming_rounds", return_value=[5, 6, 7])
    def test_nb_uses_upcoming(self, mock_upcoming):
        result = _compute_navigable_rounds("nb", ["races"], {})
        assert result == [5, 6, 7]
        mock_upcoming.assert_called_once_with(["races"], "all")

    @patch("f1_bot.handlers.round_picker.upcoming_rounds", return_value=[8, 9])
    def test_nf_uses_upcoming_with_filter(self, mock_upcoming):
        result = _compute_navigable_rounds("nf:race", ["races"], {})
        assert result == [8, 9]
        mock_upcoming.assert_called_once_with(["races"], "race")

    @patch(
        "f1_bot.handlers.round_picker.get_completed_rounds_for_session",
        return_value=[1, 2, 3],
    )
    def test_rb_uses_completed_sessions(self, mock_completed):
        result = _compute_navigable_rounds("rb", ["races"], {})
        assert result == [1, 2, 3]
        mock_completed.assert_called_once_with(["races"], "all")

    @patch(
        "f1_bot.handlers.round_picker.get_completed_rounds_for_session",
        return_value=[2, 4],
    )
    def test_rf_uses_completed_with_session_key(self, mock_completed):
        result = _compute_navigable_rounds("rf:qualifying", ["races"], {})
        assert result == [2, 4]
        mock_completed.assert_called_once_with(["races"], "qualifying")

    def test_unknown_origin_returns_empty(self):
        result = _compute_navigable_rounds("unknown", [], {})
        assert result == []


# ---------------------------------------------------------------------------
# _round_picker_callback
# ---------------------------------------------------------------------------


class TestRoundPickerCallback:
    async def test_invalid_callback_short(self):
        update = _mock_update("rpk:nb")
        ctx = MagicMock()
        await _round_picker_callback(update, ctx)
        update.callback_query.answer.assert_called_once_with(
            text="Invalid selection", show_alert=True
        )

    async def test_invalid_round_number(self):
        update = _mock_update("rpk:pit:abc")
        ctx = MagicMock()
        await _round_picker_callback(update, ctx)
        update.callback_query.answer.assert_called_once_with(
            text="Invalid selection", show_alert=True
        )

    async def test_schedule_unavailable(self):
        update = _mock_update("rpk:pit:5")
        ctx = MagicMock()
        ctx.bot_data = {"repo": MagicMock()}
        ctx.bot_data["repo"].get_schedule = AsyncMock(return_value=[])
        await _round_picker_callback(update, ctx)
        update.callback_query.answer.assert_called_once_with(
            text="Schedule unavailable", show_alert=True
        )

    @patch("f1_bot.handlers.round_picker._compute_navigable_rounds", return_value=[])
    async def test_no_navigable_rounds(self, mock_compute):
        races = [_completed_race(5)]
        update = _mock_update("rpk:pit:5")
        ctx = _mock_context(races, {"last_completed_round": 5})
        await _round_picker_callback(update, ctx)
        update.callback_query.answer.assert_called_once_with(
            text="No rounds available", show_alert=True
        )

    @patch(
        "f1_bot.handlers.round_picker._compute_navigable_rounds",
        return_value=[1, 2, 3],
    )
    async def test_displays_picker(self, mock_compute):
        races = [_completed_race(i) for i in range(1, 4)]
        update = _mock_update("rpk:pit:2")
        ctx = _mock_context(races, {"last_completed_round": 3})
        await _round_picker_callback(update, ctx)
        update.callback_query.edit_message_text.assert_called_once()
        call_kwargs = update.callback_query.edit_message_text.call_args
        assert "Select Round" in call_kwargs.args[0]
        assert call_kwargs.kwargs["parse_mode"] == ParseMode.MARKDOWN

    @patch(
        "f1_bot.handlers.round_picker._compute_navigable_rounds",
        return_value=[1, 2, 3],
    )
    async def test_snaps_to_last_if_round_not_navigable(self, mock_compute):
        races = [_completed_race(i) for i in range(1, 4)]
        update = _mock_update("rpk:pit:99")
        ctx = _mock_context(races, {"last_completed_round": 3})
        await _round_picker_callback(update, ctx)
        call_args = update.callback_query.edit_message_text.call_args
        assert "R3" in call_args.args[0]

    @patch(
        "f1_bot.handlers.round_picker._compute_navigable_rounds",
        return_value=[4, 5, 6],
    )
    async def test_snaps_to_first_for_upcoming_if_round_not_navigable(self, mock_compute):
        races = [_upcoming_race(i) for i in range(4, 7)]
        update = _mock_update("rpk:nb:99")
        ctx = _mock_context(races, {"next_upcoming_round": 4})
        await _round_picker_callback(update, ctx)
        call_args = update.callback_query.edit_message_text.call_args
        assert "R4" in call_args.args[0]

    @patch(
        "f1_bot.handlers.round_picker._compute_navigable_rounds",
        return_value=[1, 2, 3],
    )
    async def test_bad_request_swallowed(self, mock_compute):
        races = [_completed_race(i) for i in range(1, 4)]
        update = _mock_update("rpk:pit:2")
        ctx = _mock_context(races, {"last_completed_round": 3})
        update.callback_query.edit_message_text = AsyncMock(side_effect=BadRequest("unchanged"))
        await _round_picker_callback(update, ctx)
        update.callback_query.answer.assert_called_once()

    @patch(
        "f1_bot.handlers.round_picker._compute_navigable_rounds",
        return_value=[4, 5],
    )
    async def test_compound_origin_parsed_correctly(self, mock_compute):
        races = [_completed_race(4), _completed_race(5)]
        bounds = {"last_completed_round": 5}
        update = _mock_update("rpk:rf:sprint_qualifying:4")
        ctx = _mock_context(races, bounds)
        await _round_picker_callback(update, ctx)
        call_args = mock_compute.call_args[0]
        assert call_args[0] == "rf:sprint_qualifying"
        assert call_args[1] == races

    async def test_value_error_handling_for_invalid_filter(self):
        races = [_completed_race(5)]
        update = _mock_update("rpk:nf:invalid_filter:5")
        ctx = _mock_context(races, {"last_completed_round": 5})
        await _round_picker_callback(update, ctx)
        update.callback_query.answer.assert_called_once_with(
            text="Invalid selection", show_alert=True
        )
