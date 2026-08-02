"""Catalog integrity + `t()` behaviour.

The catalog is the single source of every user-facing string. These tests defend
the two properties that keep it trustworthy at merge time:

  1. Completeness — no key ships missing a translation (a gap must turn CI red,
     not silently degrade a live user to English).
  2. Placeholder parity — a translator can never drop or invent a `{placeholder}`,
     because that only blows up (KeyError/IndexError) at the instant the message
     renders, for the one language nobody tested.

`t()` itself is a pure `(key, lang) -> str` lookup and is tested for its three
contracts: loud on a typo, safe on a runtime gap, and named-kwarg interpolation
(never positional English-fragment composition).
"""

import string
from contextlib import contextmanager

import pytest

from f1_bot.formatting.i18n import COMMAND_ORDER, check_catalog_complete, t
from f1_bot.formatting.i18n.catalog import CATALOG


@contextmanager
def _patched_catalog(**entries):
    """Temporarily add/override CATALOG entries, restoring the original on exit.

    `t()` and `check_catalog_complete()` both close over the module-level CATALOG
    *object*, so mutating it in place is what they observe. We snapshot and restore
    so a patched-in gap can never leak into another test.
    """
    sentinel = object()
    saved = {k: CATALOG.get(k, sentinel) for k in entries}
    CATALOG.update(entries)
    try:
        yield
    finally:
        for k, old in saved.items():
            if old is sentinel:
                del CATALOG[k]
            else:
                CATALOG[k] = old


# --- 1. Completeness: the merge gate ---------------------------------------


def test_catalog_is_complete():
    """Every shipped language has a non-empty string for every key.

    WHY: a missing translation must fail the build, not ship and silently fall
    back to English for the users who chose the other language.
    """
    assert check_catalog_complete() == []


# --- 2. The gate actually detects a gap ------------------------------------


def test_completeness_check_detects_a_missing_translation():
    """Removing one language from one key makes the check report exactly that.

    WHY: proves the gate in test 1 is not vacuously passing — it can fail.
    """
    key = next(iter(CATALOG))
    entry_without_zh = {"en": CATALOG[key]["en"]}  # drop zh-Hant
    with _patched_catalog(**{key: entry_without_zh}):
        problems = check_catalog_complete()
    assert f"{key}[zh-Hant]" in problems
    # ...and once restored, the catalog is whole again.
    assert check_catalog_complete() == []


# --- 3. Unknown key is a loud programmer error ------------------------------


def test_t_unknown_key_raises_keyerror():
    """A typo'd key raises, never returns an empty string.

    WHY: a silent "" would ship a blank message to a user; a KeyError fails the
    developer immediately.
    """
    with pytest.raises(KeyError):
        t("schedule.this_key_does_not_exist", "en")


# --- 4. Runtime fallback to English ----------------------------------------


def test_t_falls_back_to_english_for_missing_translation():
    """A known key missing the requested language returns the English template.

    WHY: even if the completeness gate were somehow bypassed, a user must see
    English text — never a raw key or a crash.
    """
    with _patched_catalog(**{"_test.fallback_only_en": {"en": "English only"}}):
        assert t("_test.fallback_only_en", "zh-Hant") == "English only"


# --- 5. Named-kwarg interpolation ------------------------------------------


def test_t_interpolates_named_kwargs():
    """`{placeholder}` is filled from named kwargs.

    WHY: guards against re-introducing the banned pattern of composing a
    translatable template with a raw English fragment — every dynamic value must
    arrive as a named kwarg.
    """
    with _patched_catalog(**{"_test.greeting": {"en": "Hi {name}!", "zh-Hant": "嗨 {name}！"}}):
        assert t("_test.greeting", "en", name="Lewis") == "Hi Lewis!"
        assert t("_test.greeting", "zh-Hant", name="Lewis") == "嗨 Lewis！"


# --- 6. Placeholder parity across languages --------------------------------

# Two keys legitimately differ in their placeholder *sets* between en and zh-Hant.
# Both are safe because the caller always supplies the superset of names; they are
# pinned here (not blanket-skipped) so any *other* asymmetry — or a change to these
# two — still fails loudly.
#
#   datetime.date_time — en uses `{day2}` (zero-padded, reproduces %d), zh-Hant uses
#     `{day}` (unpadded, because "07月" reads wrong). `format_dt` passes BOTH, so
#     each template picks the one it wants. This is the one case where zh-Hant
#     carries a name en lacks.
#   title.remaining    — en carries `{races_word}`/`{sprints_word}` singular/plural
#     helpers that Chinese has no grammatical need for and omits. en-extra only.
_KNOWN_PLACEHOLDER_ASYMMETRY = {
    "datetime.date_time": {"en_extra": {"day2"}, "zh_extra": {"day"}},
    "title.remaining": {"en_extra": {"races_word", "sprints_word"}, "zh_extra": set()},
}


def _placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_every_key_has_matching_placeholders_across_languages():
    """en and zh-Hant use the same `{placeholders}` for every key.

    WHY: a template that references a name the caller does not supply raises only
    when *that* message renders in *that* language — the hardest bug to notice.
    Catching it at merge time is the whole point.

    Documented, pinned exceptions (`_KNOWN_PLACEHOLDER_ASYMMETRY`) are the only
    keys allowed to differ, and even they are checked exactly, so a *new*
    divergence — the dangerous kind, a name in zh-Hant that en never provides —
    still fails here.
    """
    for key, entry in CATALOG.items():
        en_fields = _placeholders(entry["en"])
        zh_fields = _placeholders(entry["zh-Hant"])
        if en_fields == zh_fields:
            continue
        assert key in _KNOWN_PLACEHOLDER_ASYMMETRY, (
            f"{key}: placeholder mismatch en={sorted(en_fields)} "
            f"zh-Hant={sorted(zh_fields)} (not in the documented allowlist)"
        )
        expected = _KNOWN_PLACEHOLDER_ASYMMETRY[key]
        assert en_fields - zh_fields == expected["en_extra"], key
        assert zh_fields - en_fields == expected["zh_extra"], key


# --- 7. Command menu catalog -----------------------------------------------


def test_command_menu_catalog_is_complete_and_translated():
    """16 commands, each with a `commands.<name>` key in both languages, and the
    zh-Hant description is a real translation (differs from the English one).

    WHY: `set_my_commands` silently ignores a mismatched list, so a missing or
    untranslated command description would never fail at runtime — only this
    assertion catches it.
    """
    assert len(COMMAND_ORDER) == 16
    for name in COMMAND_ORDER:
        key = f"commands.{name}"
        assert key in CATALOG, f"missing menu key for /{name}"
        en = CATALOG[key]["en"]
        zh = CATALOG[key]["zh-Hant"]
        assert en and zh
        assert en != zh, f"commands.{name} zh-Hant is not translated (== en)"
