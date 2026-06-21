"""Tests for pagination keyboard builders and resolve_default_round."""

from f1_bot.handlers.pagination import (
    next_filtered_keyboard,
    next_overview_keyboard,
    resolve_default_round,
    results_filtered_keyboard,
    results_overview_keyboard,
    round_keyboard,
    schedule_keyboard,
)

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
        assert len(kb.inline_keyboard) == 2
        practice_row = kb.inline_keyboard[0]
        labels = [btn.text for btn in practice_row]
        assert "FP1" in labels
        assert "FP2" in labels

    def test_has_three_rows_with_pager_when_multiple_rounds(self):
        kb = next_overview_keyboard(5, [5, 6])
        assert len(kb.inline_keyboard) == 3
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
        assert pager_row[1].callback_data == "res:back:_:3"
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
        all_btns = [btn for row in kb.inline_keyboard for btn in row]
        filter_keys = {"fp1", "fp2", "fp3", "qualifying", "sprint_qualifying", "sprint", "all"}
        for btn in all_btns:
            parts = (btn.callback_data or "").split(":")
            assert not any(
                k in parts for k in filter_keys
            ), f"Filter button found in State B: {btn.callback_data}"

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
