"""Message catalog lookup.

`t()` is a pure function of (key, lang, kwargs) — no I/O, no globals beyond the
catalog itself, and no knowledge of any chat platform.
"""

from f1_bot.formatting.i18n.catalog import CATALOG

SHIPPED_LANGS: tuple[str, ...] = ("en", "zh-Hant")
DEFAULT_LANG = "en"


def t(key: str, lang: str, /, **kwargs) -> str:
    """Look up `key` in `lang`, interpolating `kwargs`.

    Unknown key → KeyError (programmer error, surfaced loudly).
    Known key with a missing translation → the English template (runtime safety net).

    `key` and `lang` are **positional-only** so that a catalog template is free to
    use `{key}` or `{lang}` as a placeholder name. Without the `/` they collide:
    `t("settings.lang_saved", code, lang=...)` binds `lang` both positionally and
    by keyword and raises TypeError — which silently killed the whole `/language`
    command. Same class as the Pydantic field-shadowing gotcha in CLAUDE.md.
    """
    entry = CATALOG.get(key)
    if entry is None:
        raise KeyError(f"Unknown i18n key: {key}")
    template = entry.get(lang) or entry["en"]
    return template.format(**kwargs) if kwargs else template


def lang_name(lang: str, display_lang: str = DEFAULT_LANG) -> str:
    """Human-readable name of `lang`, rendered in `display_lang`.

    Unknown codes echo back verbatim.
    """
    key = f"settings.lang_name_{lang.replace('-', '_').lower()}"
    if key not in CATALOG:
        return lang
    return t(key, display_lang)


def check_catalog_complete() -> list[str]:
    """Return a list of `key[lang]` problems — empty means the catalog is complete."""
    problems: list[str] = []
    for key, entry in sorted(CATALOG.items()):
        for lang in SHIPPED_LANGS:
            value = entry.get(lang)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{key}[{lang}]")
    return problems
