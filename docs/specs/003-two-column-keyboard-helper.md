# Spec 003 — Shared `two_column_keyboard` helper

**Status:** Draft — awaiting review
**Type:** Refactor (reuse cleanup, no behavior change)
**Date:** 2026-07-29

## Problem statement

The 2-column inline-keyboard chunking idiom

```python
[buttons[i : i + 2] for i in range(0, len(buttons), 2)]
```

is copy-pasted **verbatim in three places**:

- `handlers/compare.py:78` — inside `_menu_keyboard` (the `/compare` driver grid)
- `handlers/extras.py:31` — inside `_driver_menu_keyboard` (the `/driver` grid)
- `handlers/extras.py:44` — inside `_circuit_menu_keyboard` (the `/circuit` grid)

Three independent copies of the same row-packing expression means a future change
to grid layout (e.g. 3 columns, or an odd-count tweak) must be made in three
places, and a reader has to confirm all three are actually identical. This is a
pure reuse smell surfaced by the `/simplify` review — the expression is trivial,
but it is duplicated shared infrastructure, and the project already has a home for
shared keyboard builders (`handlers/pagination.py`).

## Goals

- Extract the 2-column chunking into a single shared helper
  `two_column_keyboard(buttons)` in `handlers/pagination.py`, alongside the other
  shared keyboard builders.
- Update the three call sites to use it.
- **Zero behavior change.** Byte-for-byte identical keyboards must be produced;
  the existing test suites for `/compare`, `/driver`, and `/circuit` are the
  contract and must stay green without modification.

## Non-goals

- **Do NOT fold in `race_data.py:160` (`_laps_driver_picker_keyboard`).** That site
  looks similar but is materially different: it uses `cols = 4`, and it chunks the
  *input list* (`driver_ids`) and builds buttons *inside* the loop, not a
  pre-built `buttons` list. Making `two_column_keyboard` accommodate it would force
  a `cols` parameter and a second "chunk-then-build" mode — over-generalizing a
  helper to fit a case that does not share its shape. It stays as-is. (If a general
  `chunk(seq, cols)` is ever wanted, that is a separate future spec.)
- **No signature change to the three affected keyboard functions.** `_menu_keyboard`,
  `_driver_menu_keyboard`, `_circuit_menu_keyboard` keep their current parameters
  and return types (`InlineKeyboardMarkup`). Only their internal chunking line
  changes.
- **No change to the `/compare` exclude-driver or 64-byte-callback-data logic.**
  That logic runs while *building* the `buttons` list, before chunking; it is
  untouched.
- **No new file.** The helper lives in `pagination.py`, the existing home for
  shared keyboard builders. (Two handlers gain a one-line import *of* that module —
  see Design — but no new module is created.)

## Design

### The helper

Add to `handlers/pagination.py` (near the top, with the other builders):

```python
def two_column_keyboard(buttons: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    """Pack a flat list of buttons into a 2-column keyboard (last row may hold one)."""
    return InlineKeyboardMarkup([buttons[i : i + 2] for i in range(0, len(buttons), 2)])
```

**Why return `InlineKeyboardMarkup`, not the raw row list:** every existing builder
in `pagination.py` (`round_keyboard`, `schedule_keyboard`, `next_overview_keyboard`,
… — all 12) returns `InlineKeyboardMarkup`. Returning the wrapped markup keeps
`two_column_keyboard` consistent with its neighbors (Rule 11) and lets each caller
drop a wrapping layer. The per-button logic that `compare._menu_keyboard` runs
(exclude driver A, enforce the 64-byte callback_data cap) all happens while
*assembling* the `buttons` list — it is complete before chunking begins, so it does
not depend on the helper leaving the markup unwrapped. No current caller needs to
prepend or append its own rows, so a rows-out contract would add composability that
has no user (YAGNI); if such a caller ever appears, switching the helper to return
rows is a one-line change.

### Call-site changes

**`compare.py:57-77`** — `_menu_keyboard`. Add `two_column_keyboard` to a new
import from `f1_bot.handlers.pagination`, and change the final line from:

```python
return InlineKeyboardMarkup([buttons[i : i + 2] for i in range(0, len(buttons), 2)])
```
to:
```python
return two_column_keyboard(buttons)
```

**`extras.py:22-32`** — `_driver_menu_keyboard`. Change:

```python
keyboard = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
return InlineKeyboardMarkup(keyboard)
```
to:
```python
return two_column_keyboard(buttons)
```

**`extras.py:35-45`** — `_circuit_menu_keyboard`. Same change as above.

Both `compare.py` and `extras.py` currently have **no** import from
`f1_bot.handlers.pagination`, so a new import line is added to each. Their existing
`InlineKeyboardButton` imports stay (both still construct buttons); their
`InlineKeyboardMarkup` imports also stay — `extras.py` still uses it at lines
242/282, and `compare.py` still uses it in `_back_keyboard`.

### Import-cycle check

`pagination.py` currently imports from `formatting.messages`, `formatting.emoji`,
and `utils.sessions` — it does **not** import from `handlers.compare` or
`handlers.extras`. Those two handlers importing *from* `pagination` introduces no
cycle (the dependency already flows handlers → pagination for other builders; e.g.
`schedule.py`/`results.py` import pagination builders). Confirmed one-directional.

## Error handling

None to add. `two_column_keyboard` is a pure total function over a list; an empty
list yields `InlineKeyboardMarkup([])` (an empty keyboard), exactly as the inlined
expression wrapped in `InlineKeyboardMarkup(...)` does today. No new failure modes.

## Testing approach

The behavior contract is "identical keyboards," so the **existing** handler tests
are the primary guard and must pass unmodified:

- `tests/test_handlers/test_compare.py` — asserts the `/compare` grid shape,
  including the 2-column packing and the step-2 exclude-A behavior.
- `tests/test_handlers/test_extras.py` — asserts the `/driver` and `/circuit`
  menu grids (confirmed present; 8 keyboard/menu assertions).

Add **one** focused unit test for the helper itself, encoding *why* it exists —
that it packs into rows of two with a possible singleton last row. The helper
returns `InlineKeyboardMarkup`, whose `.inline_keyboard` is a **tuple-of-tuples**
(PTB gotcha — assert with `()`, not `[]`):

- `two_column_keyboard([]).inline_keyboard` → `()`
- `two_column_keyboard([b1]).inline_keyboard` → `((b1,),)` (odd count: last row holds one)
- `two_column_keyboard([b1, b2, b3]).inline_keyboard` → `((b1, b2), (b3,))`

Place it in the existing `tests/test_handlers/test_pagination.py`, following that
file's `class Test...:` grouping convention (e.g. `class TestTwoColumnKeyboard:`).

Run after the change:
```bash
uv run pytest tests/test_handlers/test_compare.py tests/test_handlers/test_extras.py -q
uv run ruff check src/ tests/ && uv run ruff format src/ tests/
```

## Rollout / risk

- **Risk: very low.** Single trivial pure function; three mechanical call-site
  swaps; no data-layer, scheduler, or callback-format change.
- **Blast radius:** `handlers/pagination.py` (+helper), `handlers/compare.py`
  (1 line + import), `handlers/extras.py` (2 lines + import), one new helper test.
- **Reversibility:** trivially revertible; the inlined expression is preserved in
  git-less form here in the spec if a rollback is ever needed.

## Out-of-scope follow-ups (recorded, not part of this spec)

- `race_data.py:160` general `chunk(seq, cols)` helper — only if a third
  variable-column caller appears.
- The two deeper `/compare` altitude items from the `/simplify` review
  (`_finished` → model, `_aggregate`/`_real_drivers` → Repository) are explicitly
  **not** bundled here; they were assessed and deferred separately.
