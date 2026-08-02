"""Guard C — external free text interpolated into Markdown must be escaped.

The bot renders with legacy ``ParseMode.MARKDOWN``. A driver, team, circuit or
country name coming from Jolpica/OpenF1 that happens to contain ``_``, ``*``,
``` ` ``` or ``[`` is interpolated straight into a catalog template — over half
of which already carry Markdown markers of their own. Telegram then either
mis-renders the message or rejects it outright with ``BadRequest``, and handlers
swallow ``BadRequest`` by convention, so the user simply sees nothing happen.

This is an AST guard rather than a grep because the defect it exists to prevent
was *found* by grepping and the grep missed most of it: three free-text kwargs in
a single ``t()`` call, two lines apart, where the pattern only matched the first.

**Scope: ``formatting/`` only.** That is where Markdown message bodies are built.
``handlers/`` is deliberately excluded — its free-text interpolations go into
inline-button labels and ``answer(show_alert=True)`` popups, neither of which
Telegram parses as Markdown, so escaping there would surface literal backslashes
to the user. The two handler sites that *do* build message text
(``notifications.py`` round header, ``pagination.round_picker_text``) escape at
the assignment.
"""

import ast
import pathlib

# kwarg names whose values carry free text from an external API.
# Add a name here when a new catalog template interpolates external text.
FREE_TEXT_KWARGS = {
    "name",
    "circuit",
    "locality",
    "country",
    "team",
    "nationality",
    "champion",
    "driver",
}

# Helpers whose return value is already safe: _esc() escapes, t() returns catalog
# text, and the *_label helpers resolve a catalog key.
SAFE_CALLS = {"_esc", "t", "session_label", "session_short_label", "region_label", "timing_label"}

FORMATTING_ROOT = pathlib.Path(__file__).resolve().parents[2] / "src" / "f1_bot" / "formatting"


def _is_safe_value(node: ast.expr, escaped_names: set[str]) -> bool:
    """True if this expression cannot smuggle unescaped external text into Markdown."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id in SAFE_CALLS
    # `name` where the enclosing function did `name = _esc(...)`
    if isinstance(node, ast.Name):
        return node.id in escaped_names
    # `_esc(x) or "—"` / `a if c else b` — safe only when every branch is
    if isinstance(node, ast.BoolOp):
        return all(_is_safe_value(v, escaped_names) for v in node.values)
    if isinstance(node, ast.IfExp):
        return _is_safe_value(node.body, escaped_names) and _is_safe_value(
            node.orelse, escaped_names
        )
    return False


def _escaped_local_names(func: ast.AST) -> set[str]:
    """Locals assigned from a safe call, e.g. ``title = _esc(race.name)``."""
    names: set[str] = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        if not _is_safe_value(node.value, names):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def _violations(root: pathlib.Path = FORMATTING_ROOT) -> list[str]:
    found = []
    for path in sorted(root.rglob("*.py")):
        if "i18n/catalog" in path.as_posix():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))

        for func in ast.walk(tree):
            if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            escaped_names = _escaped_local_names(func)

            for node in ast.walk(func):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "t"
                ):
                    continue
                key = (
                    node.args[0].value
                    if node.args and isinstance(node.args[0], ast.Constant)
                    else "<dynamic>"
                )
                for kw in node.keywords:
                    if kw.arg in FREE_TEXT_KWARGS and not _is_safe_value(kw.value, escaped_names):
                        found.append(
                            f"{path.name}:{kw.value.lineno} "
                            f"t({key!r}) {kw.arg}={ast.unparse(kw.value)}"
                        )
    return found


def test_free_text_kwargs_are_escaped():
    """A raw API string reaching a Markdown template is a message the user never sees."""
    violations = _violations()
    assert not violations, "Unescaped external free text in t() calls:\n" + "\n".join(
        f"  {v}" for v in violations
    )


def test_guard_detects_a_planted_violation(tmp_path):
    """The guard must be able to fail — otherwise it is decoration.

    Guard A and Guard B both passed while three real defects sat in the tree, so a
    guard that has never been shown to fire is not evidence of anything.
    """
    fake = tmp_path / "formatting"
    fake.mkdir()
    (fake / "leaky.py").write_text(
        "def render(race, ctx):\n"
        "    return t('schedule.location', ctx.lang, circuit=race.circuit.name)\n",
        encoding="utf-8",
    )
    violations = _violations(fake)
    assert len(violations) == 1
    assert "circuit=race.circuit.name" in violations[0]


def test_guard_accepts_escaping_at_the_assignment(tmp_path):
    """``title = _esc(race.name)`` then ``t(..., title=title)`` must not be flagged.

    Five real call sites use this shape; a guard that cannot follow it would be
    silenced with noqa comments within a week.
    """
    fake = tmp_path / "formatting"
    fake.mkdir()
    (fake / "clean.py").write_text(
        "def render(race, ctx):\n"
        "    name = _esc(race.name)\n"
        "    return t('schedule.next_race_header', ctx.lang, name=name)\n",
        encoding="utf-8",
    )

    assert _violations(fake) == []
