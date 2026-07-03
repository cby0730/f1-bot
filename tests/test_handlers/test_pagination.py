"""Tests for pagination keyboard builders and resolve_default_round."""

from f1_bot.handlers.pagination import (
    _origin_to_callback,
    next_filtered_keyboard,
    next_overview_keyboard,
    resolve_default_round,
    results_filtered_keyboard,
    results_overview_keyboard,
    round_keyboard,
    round_picker_keyboard,
    round_picker_text,
    schedule_keyboard,
)
from f1_bot.models.race import Circuit, Race

# ---------------------------------------------------------------------------
# round_keyboard
# ---------------------------------------------------------------------------


class TestRoundKeyboard:
    def test_empty_navigable_rounds_returns_empty_keyboard(self):
        kb = round_keyboard("pit", 1, [])
        assert kb.inline_keyboard == ((),)

    def test_single_round_no_prev_no_next(self):
        kb = round_keyboard("pit", 3, [3])
        row = kb.inline_keyboard[0]
        assert len(row) == 1
        assert "R3/3" in row[0].text

    def test_first_round_no_prev_button(self):
        kb = round_keyboard("pit", 1, [1, 2, 3])
        row = kb.inline_keyboard[0]
        # Should have position + next only
        assert len(row) == 2
        assert "R1/3" in row[0].text
        assert row[1].text == "▶"
        assert row[1].callback_data == "pit:2"

    def test_last_round_no_next_button(self):
        kb = round_keyboard("pit", 3, [1, 2, 3])
        row = kb.inline_keyboard[0]
        assert len(row) == 2
        assert row[0].text == "◀"
        assert row[0].callback_data == "pit:2"
        assert "R3/3" in row[1].text

    def test_middle_round_both_arrows(self):
        kb = round_keyboard("pit", 2, [1, 2, 3])
        row = kb.inline_keyboard[0]
        assert len(row) == 3
        assert row[0].text == "◀"
        assert row[0].callback_data == "pit:1"
        assert "R2/3" in row[1].text
        assert row[2].text == "▶"
        assert row[2].callback_data == "pit:3"

    def test_current_round_not_in_list_falls_back_to_last(self):
        """When current_round is missing from navigable_rounds, falls back to last index."""
        kb = round_keyboard("pit", 99, [1, 2, 3])
        row = kb.inline_keyboard[0]
        # Falls to idx = total-1 = 2 (round 3), so has prev but no next
        assert row[0].text == "◀"
        assert "R99/3" in row[1].text  # Still shows the requested round in label


# ---------------------------------------------------------------------------
# schedule_keyboard
# ---------------------------------------------------------------------------


class TestScheduleKeyboard:
    def test_empty_returns_empty_keyboard(self):
        kb = schedule_keyboard("next", 1, [])
        assert kb.inline_keyboard == ((),)

    def test_current_not_in_list_falls_back_to_first(self):
        kb = schedule_keyboard("next", 99, [5, 6, 7])
        row = kb.inline_keyboard[0]
        # Falls back to idx=0 (round 5), no prev, has next
        assert len(row) == 2
        assert "R99/7" in row[0].text
        assert row[1].text == "▶"


# ---------------------------------------------------------------------------
# next_overview_keyboard
# ---------------------------------------------------------------------------


class TestNextOverviewKeyboard:
    def test_has_no_pager_when_single_round(self):
        kb = next_overview_keyboard(5, [5])
        assert len(kb.inline_keyboard) == 3  # practice + competitive + bell
        practice_row = kb.inline_keyboard[0]
        labels = [btn.text for btn in practice_row]
        assert "FP1" in labels
        assert "FP2" in labels

    def test_has_three_rows_with_pager_when_multiple_rounds(self):
        kb = next_overview_keyboard(5, [5, 6])
        assert len(kb.inline_keyboard) == 4  # pager + practice + competitive + bell
        pager_row = kb.inline_keyboard[0]
        assert len(pager_row) == 2  # R5/6 and ▶
        assert pager_row[0].text == "R5/6"
        assert pager_row[1].text == "▶"

    def test_practice_row_buttons(self):
        kb = next_overview_keyboard(5, [5, 6])
        practice_row = kb.inline_keyboard[1]
        labels = [btn.text for btn in practice_row]
        assert "FP1" in labels
        assert "FP2" in labels
        assert "FP3" in labels
        assert "Q" in labels

    def test_competitive_row_buttons(self):
        kb = next_overview_keyboard(5, [5, 6])
        comp_row = kb.inline_keyboard[2]
        labels = [btn.text for btn in comp_row]
        assert "SQ" in labels
        assert "SPR" in labels
        assert "Race" in labels
        assert "All" not in labels

    def test_callback_data_format(self):
        kb = next_overview_keyboard(7, [7, 8])
        btn = kb.inline_keyboard[1][0]  # FP1 button
        assert btn.callback_data == "next:filtered:fp1:7"


# ---------------------------------------------------------------------------
# results_overview_keyboard
# ---------------------------------------------------------------------------


class TestResultsOverviewKeyboard:
    def test_no_active_key_all_plain(self):
        kb = results_overview_keyboard(3, completed_rounds=[3])
        for row in kb.inline_keyboard:
            for btn in row:
                assert not btn.text.startswith("·")
        assert len(kb.inline_keyboard) == 2

    def test_with_pager_row(self):
        kb = results_overview_keyboard(3, completed_rounds=[1, 2, 3, 4])
        assert len(kb.inline_keyboard) == 3
        pager_row = kb.inline_keyboard[0]
        assert len(pager_row) == 3  # Prev button, middle label, and Next button
        assert pager_row[0].text == "◀"
        assert pager_row[0].callback_data == "res:back:_:2"
        assert pager_row[1].text == "R3/4"
        assert pager_row[1].callback_data == "rpk:rb:3"
        assert pager_row[2].text == "▶"
        assert pager_row[2].callback_data == "res:back:_:4"

    def test_active_key_highlighted(self):
        kb = results_overview_keyboard(3, completed_rounds=[3], active_key="race")
        # Find the race button
        found = False
        for row in kb.inline_keyboard:
            for btn in row:
                if "race" in btn.callback_data.split(":"):
                    if btn.text == "·Race·":
                        found = True
        assert found, "Race button should be highlighted with ·Race·"

    def test_callback_data_format(self):
        kb = results_overview_keyboard(5, completed_rounds=[5], active_key="qualifying")
        btn = kb.inline_keyboard[0][-1]  # Q button (last in practice row)
        assert btn.callback_data == "res:filtered:qualifying:5"


# ---------------------------------------------------------------------------
# results_filtered_keyboard
# ---------------------------------------------------------------------------


class TestResultsFilteredKeyboard:
    def test_includes_back_button(self):
        kb = results_filtered_keyboard(3, [1, 2, 3], "race")
        last_row = kb.inline_keyboard[-1]
        assert any("Back" in btn.text for btn in last_row)

    def test_back_button_callback_format(self):
        kb = results_filtered_keyboard(5, [4, 5, 6], "qualifying")
        last_row = kb.inline_keyboard[-1]
        back_btn = [btn for btn in last_row if "Back" in btn.text][0]
        assert back_btn.callback_data == "res:back:_:5"

    def test_state_b_has_no_filter_row(self):
        """State B should only have nav row + back row, no session filter buttons."""
        kb = results_filtered_keyboard(3, [1, 2, 3], "race")
        assert len(kb.inline_keyboard) == 2
        nav_texts = {btn.text for btn in kb.inline_keyboard[0]}
        assert nav_texts & {"◀", "▶"}
        back_texts = {btn.text for btn in kb.inline_keyboard[1]}
        assert any("Back" in t for t in back_texts)

    def test_state_b_nav_row_is_first(self):
        """Nav row (◀ ▶) should be the first row in State B keyboard."""
        kb = results_filtered_keyboard(5, [4, 5, 6], "qualifying")
        first_row = kb.inline_keyboard[0]
        texts = [btn.text for btn in first_row]
        assert "◀" in texts
        assert "▶" in texts

    def test_state_b_single_round_back_only(self):
        """When only one navigable round exists, State B has nav row with label and back row."""
        kb = results_filtered_keyboard(3, [3], "race")
        assert len(kb.inline_keyboard) == 2
        assert any("R3/3" in btn.text for btn in kb.inline_keyboard[0])
        assert any("Back" in btn.text for btn in kb.inline_keyboard[1])


# ---------------------------------------------------------------------------
# next_filtered_keyboard
# ---------------------------------------------------------------------------


class TestNextFilteredKeyboard:
    def test_back_button_present(self):
        kb = next_filtered_keyboard(3, [1, 2, 3], "race")
        last_row = kb.inline_keyboard[-1]
        assert any("Back" in btn.text for btn in last_row)

    def test_back_callback_format(self):
        kb = next_filtered_keyboard(5, [4, 5, 6], "practice")
        last_row = kb.inline_keyboard[-1]
        back_btn = [btn for btn in last_row if "Back" in btn.text][0]
        assert back_btn.callback_data == "next:back:_:5"

    def test_nav_buttons_with_multiple_rounds(self):
        kb = next_filtered_keyboard(5, [4, 5, 6], "race")
        nav_row = kb.inline_keyboard[0]
        texts = [btn.text for btn in nav_row]
        assert "◀" in texts
        assert "▶" in texts


# ---------------------------------------------------------------------------
# resolve_default_round
# ---------------------------------------------------------------------------


class TestResolveDefaultRound:
    def test_returns_last_completed_round(self):
        bounds = {"last_completed_round": 7, "completed_sprint_rounds": [3, 5]}
        assert resolve_default_round(bounds) == 7

    def test_no_completed_round_returns_none(self):
        bounds = {"last_completed_round": None, "completed_sprint_rounds": []}
        assert resolve_default_round(bounds) is None

    def test_sprint_only_returns_last_sprint(self):
        bounds = {"last_completed_round": 7, "completed_sprint_rounds": [3, 5]}
        assert resolve_default_round(bounds, sprint_only=True) == 5

    def test_sprint_only_no_sprints_returns_none(self):
        bounds = {"last_completed_round": 7, "completed_sprint_rounds": []}
        assert resolve_default_round(bounds, sprint_only=True) is None

    def test_missing_key_returns_none(self):
        bounds = {}
        assert resolve_default_round(bounds) is None
        assert resolve_default_round(bounds, sprint_only=True) is None


# ---------------------------------------------------------------------------
# _origin_to_callback
# ---------------------------------------------------------------------------


def _make_race(rnd: int, name: str = "Test GP", country: str = "UK") -> Race:
    from datetime import date

    return Race(
        season=2025,
        round=rnd,
        name=name,
        circuit=Circuit(circuit_id="test", name="Test", locality="Test", country=country),
        date=date(2025, 6, 1),
    )


class TestOriginToCallback:
    def test_pit(self):
        assert _origin_to_callback("pit", 5) == "pit:5"

    def test_lap(self):
        assert _origin_to_callback("lap", 3) == "lap:3:s"

    def test_nb(self):
        assert _origin_to_callback("nb", 10) == "next:back:_:10"

    def test_nf(self):
        assert _origin_to_callback("nf:race", 7) == "next:filtered:race:7"

    def test_rb(self):
        assert _origin_to_callback("rb", 4) == "res:back:_:4"

    def test_rf(self):
        assert _origin_to_callback("rf:qualifying", 2) == "res:filtered:qualifying:2"

    def test_rf_sprint_qualifying(self):
        assert _origin_to_callback("rf:sprint_qualifying", 8) == "res:filtered:sprint_qualifying:8"


# ---------------------------------------------------------------------------
# round_picker_keyboard
# ---------------------------------------------------------------------------


class TestRoundPickerKeyboard:
    def test_four_column_layout(self):
        races = [_make_race(i) for i in range(1, 9)]
        kb = round_picker_keyboard("pit", 3, [1, 2, 3, 4, 5, 6, 7, 8], races)
        grid_rows = kb.inline_keyboard[:-1]
        assert len(grid_rows) == 2
        assert all(len(row) == 4 for row in grid_rows)

    def test_partial_last_row(self):
        races = [_make_race(i) for i in range(1, 6)]
        kb = round_picker_keyboard("pit", 3, [1, 2, 3, 4, 5], races)
        grid_rows = kb.inline_keyboard[:-1]
        assert len(grid_rows) == 2
        assert len(grid_rows[0]) == 4
        assert len(grid_rows[1]) == 1

    def test_current_round_highlighted(self):
        races = [_make_race(1), _make_race(2), _make_race(3)]
        kb = round_picker_keyboard("pit", 2, [1, 2, 3], races)
        all_btns = [btn for row in kb.inline_keyboard[:-1] for btn in row]
        highlighted = [btn for btn in all_btns if btn.text.startswith("·")]
        assert len(highlighted) == 1
        assert "2" in highlighted[0].text

    def test_back_button_present(self):
        races = [_make_race(1), _make_race(2)]
        kb = round_picker_keyboard("pit", 1, [1, 2], races)
        back_row = kb.inline_keyboard[-1]
        assert len(back_row) == 1
        assert "Back" in back_row[0].text
        assert back_row[0].callback_data == "pit:1"

    def test_picker_buttons_emit_original_callbacks(self):
        races = [_make_race(i) for i in range(1, 4)]
        kb = round_picker_keyboard("rb", 2, [1, 2, 3], races)
        btn = kb.inline_keyboard[0][0]
        assert btn.callback_data == "res:back:_:1"

    def test_back_button_uses_current_round(self):
        races = [_make_race(1), _make_race(2)]
        kb = round_picker_keyboard("nf:race", 2, [1, 2], races)
        back_btn = kb.inline_keyboard[-1][0]
        assert back_btn.callback_data == "next:filtered:race:2"


# ---------------------------------------------------------------------------
# round_picker_text
# ---------------------------------------------------------------------------


class TestRoundPickerText:
    def test_contains_round_and_name(self):
        races = [_make_race(5, "British Grand Prix")]
        text = round_picker_text(5, races)
        assert "R5" in text
        assert "British Grand Prix" in text
        assert "Select Round" in text

    def test_unknown_round(self):
        text = round_picker_text(99, [])
        assert "R99" in text
        assert "Unknown" in text

    def test_escapes_markdown_chars(self):
        races = [_make_race(1, "Test_GP")]
        text = round_picker_text(1, races)
        assert "Test\\_GP" in text
