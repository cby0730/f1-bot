"""Anti-regression guards — prove the catalog is actually *used*, not merely filled.

A completeness check (test_catalog.py) proves every key is translated. It does
**not** stop a handler from shipping an inline literal that never went through the
catalog — which is exactly how the original stray `/compare` zh strings arose, and
how the un-migrated `answer()` toasts survive today. These two guards close that gap:

  Guard A (hard gate): no hardcoded CJK anywhere under `handlers/`/`formatting/`
    outside the catalog. Any Chinese in a string literal is a leaked translation —
    zero heuristics, zero false positives.

  Guard B (hard gate): no bare English string literal handed straight to a Telegram
    output call (`reply_text`/`edit_message_text`/`answer`). Catches hardcoded
    *English* at the point it reaches a user.

Both guards are scanned with `ast`, so comments and docstrings — legitimate places
to *document* a CJK example — are ignored automatically; only real string literals
that ship to users are inspected.

DESIGN: strict, ZERO-baseline gates. The i18n migration (standings/title/extras/
compare — and finally round_picker) has fully landed, so BOTH guards now carry an
empty leak baseline: no hardcoded CJK and no bare English literal reaches a user
anywhere under `handlers/` or `formatting/`. Any such literal keeps its gate RED
(with file:line) until it is routed through the catalog. There is deliberately no
per-file/per-line leak pin that a future real leak could hide behind. The ONLY
allowlisted literals are genuinely untranslatable tokens per the spec's non-goals:
the empty string and the universal motorsport abbreviations DSQ/DNS/DNF/TBD
(`_BOUNDARY_ALLOW`).
"""

import ast
import re
from collections.abc import Iterable
from pathlib import Path

import f1_bot

_SRC = Path(f1_bot.__file__).parent
_CATALOG_DIR = _SRC / "formatting" / "i18n" / "catalog"

# CJK ideographs + Kangxi/CJK punctuation + fullwidth forms. Chinese punctuation
# (、，。！：（）) lives in the fullwidth/CJK-symbols blocks, so a leaked sentence is
# caught even if it were somehow ideograph-free.
_CJK = re.compile(r"[　-〿㐀-䶿一-鿿豈-﫿＀-￯]")

_BOUNDARY_TARGETS = ("reply_text", "edit_message_text", "answer")
# The ONLY non-translated literals allowed at an output boundary: empty scaffolding
# + universal motorsport abbreviations (spec non-goal: DSQ/DNS/DNF/TBD are stable
# across languages). Nothing else — no leak baseline lives here.
_BOUNDARY_ALLOW = frozenset({"", "DSQ", "DNS", "DNF", "TBD"})


def _scanned_files() -> list[Path]:
    """Every `.py` under handlers/ and formatting/, minus the catalog itself."""
    out: list[Path] = []
    for base in ("handlers", "formatting"):
        for p in (_SRC / base).rglob("*.py"):
            if _CATALOG_DIR in p.parents:
                continue
            out.append(p)
    return out


def _docstring_node_ids(tree: ast.AST) -> set[int]:
    """id()s of the Constant nodes that are module/class/function docstrings.

    Docstrings are string literals too, but they never reach a user — they are
    where a developer legitimately shows a CJK example (the `/compare` module
    docstring, the `🌐 Language / 語言` note in start.py). Excluding them keeps
    Guard A to *shipped* strings only.
    """
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def scan_cjk_literals(paths: Iterable[Path], root: Path) -> set[tuple[str, int, str]]:
    """(relpath, lineno, text) for every non-docstring str literal containing CJK."""
    hits: set[tuple[str, int, str]] = set()
    for p in paths:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        docstrings = _docstring_node_ids(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
                and _CJK.search(node.value)
            ):
                hits.add((p.relative_to(root).as_posix(), node.lineno, node.value))
    return hits


def _boundary_text_arg(call: ast.Call) -> ast.expr | None:
    """The `text` argument of a reply/edit/answer call (first positional or text=)."""
    if call.args:
        return call.args[0]
    for kw in call.keywords:
        if kw.arg == "text":
            return kw.value
    return None


def scan_boundary_literals(
    paths: Iterable[Path], root: Path, targets: Iterable[str] = _BOUNDARY_TARGETS
) -> set[tuple[str, int, str, str]]:
    """(relpath, lineno, target, text) for bare str literals at an output boundary.

    A `t(...)` call or a variable reference is *not* a literal and passes; only a
    bare, non-allowlisted string constant is flagged.
    """
    targets = set(targets)
    hits: set[tuple[str, int, str, str]] = set()
    for p in paths:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in targets
            ):
                arg = _boundary_text_arg(node)
                if (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and arg.value not in _BOUNDARY_ALLOW
                ):
                    hits.add(
                        (p.relative_to(root).as_posix(), node.lineno, node.func.attr, arg.value)
                    )
    return hits


# ---------------------------------------------------------------------------
# Guard A — no hardcoded CJK (the original sin)
# ---------------------------------------------------------------------------


def test_guard_a_scanner_detects_cjk_and_ignores_docs(tmp_path):
    """The scanner flags a CJK *string literal* but not a CJK comment/docstring.

    WHY: proves Guard A actually works (not vacuously green) and that its exclusion
    of comments/docstrings is real — otherwise the real-tree gate below would be
    meaningless. Independent of the production tree, so it passes even while the
    real-tree gate is red mid-migration.
    """
    leaky = tmp_path / "leaky.py"
    leaky.write_text(
        '"""模組說明 — a docstring, must be ignored."""\n'
        "# 這是中文註解 — a comment, must be ignored\n"
        'LABEL = "賽車"  # a real literal, must be caught\n',
        encoding="utf-8",
    )
    clean = tmp_path / "clean.py"
    clean.write_text('X = "hello world"\n', encoding="utf-8")

    hits = scan_cjk_literals([leaky, clean], tmp_path)

    assert hits == {("leaky.py", 3, "賽車")}


def test_guard_a_no_cjk_leaks_in_source():
    """ZERO hardcoded CJK in the real tree — every Chinese string lives in the catalog.

    WHY: this is the hard gate against the exact regression that motivated the whole
    guard — a stray inline zh string (the original `/compare` `_back_keyboard` leak).
    There is deliberately NO leak allowlist: a hardcoded translation keeps this gate
    RED (with file:line) until it is moved into the catalog, never pinned green. Now
    that compare.py is migrated the baseline is genuinely zero — every Chinese string
    ships from the catalog.
    """
    leaks = scan_cjk_literals(_scanned_files(), _SRC)
    assert leaks == set(), (
        "Hardcoded CJK found — move it into the catalog and render via t(): "
        + ", ".join(f"{rel}:{line} {text!r}" for rel, line, text in sorted(leaks))
    )


# ---------------------------------------------------------------------------
# Guard B — no bare English literal at a Telegram output boundary
# ---------------------------------------------------------------------------


def test_guard_b_scanner_distinguishes_literals_from_t_and_vars(tmp_path):
    """A bare literal is flagged; `t(...)`, a variable, "", and DSQ/DNS/DNF/TBD pass.

    WHY: proves Guard B catches hardcoded English *and* that its allowlist +
    "must be a bare literal" rule work — so the real-tree gate is trustworthy and
    doesn't flag correctly-i18n'd call sites. Independent of the production tree.
    """
    f = tmp_path / "handler.py"
    f.write_text(
        "async def h(update, q, var):\n"
        '    await update.reply_text("hardcoded")\n'          # flagged
        '    await update.reply_text(t("k", lang))\n'         # ok: a call
        "    await update.reply_text(var)\n"                  # ok: a variable
        '    await update.reply_text("")\n'                   # ok: allowlisted
        '    await update.reply_text("DNF")\n'                # ok: allowlisted
        '    await q.answer("also hardcoded")\n'              # flagged
        '    await q.edit_message_text(text="edited literal")\n'  # flagged (text=)
        '    await q.edit_message_text(text=t("k", lang))\n',  # ok: a call
        encoding="utf-8",
    )

    flagged = {(target, text) for _rel, _line, target, text in scan_boundary_literals([f], tmp_path)}

    assert flagged == {
        ("reply_text", "hardcoded"),
        ("answer", "also hardcoded"),
        ("edit_message_text", "edited literal"),
    }


def test_guard_b_no_hardcoded_english_at_boundary():
    """ZERO bare English literals reach a user — every boundary string goes through t().

    WHY: proves the catalog is actually *used* at the output boundary, not merely
    filled. There is NO leak baseline: a hardcoded toast keeps this gate RED (with
    file:line) until it is routed through `t()`; only genuinely untranslatable tokens
    (""/DSQ/DNS/DNF/TBD) are allowlisted. `round_picker.py` — the last un-migrated
    handler, and formerly the sole documented gap — is now clean too (its toasts route
    through `common.invalid_selection` / `common.schedule_unavailable` /
    `common.no_rounds_available`), so the baseline is genuinely empty.

    Scope (honestly stated): covers `reply_text`/`edit_message_text`/`answer`
    first-positional or `text=` arguments. It does NOT inspect composed calls like
    `no_data_message("driver list")` (a call, not a literal) — that English-fragment
    composition is a separate concern.
    """
    hits = scan_boundary_literals(_scanned_files(), _SRC)
    offenders = {(rel, line, text) for rel, line, _target, text in hits}
    assert offenders == set(), (
        "Hardcoded English at a Telegram output boundary (route it through t()): "
        + ", ".join(f"{rel}:{line} {text!r}" for rel, line, text in sorted(offenders))
    )
