"""Language actually reaching rendered output — dates, countdowns, the push
notification path, and the previously-leaking `/compare` strings.

These are the surfaces where a wrong-language render would be *visible* to a user,
including the one surface (`send_notifications`) that has no `Update` and therefore
cannot use `resolve_context`.
"""

import locale
import re
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.messages import format_driver_comparison
from f1_bot.formatting.timezone import format_countdown, format_dt
from f1_bot.models.driver import Driver
from f1_bot.models.notification import NotificationSubscription
from f1_bot.scheduler.notification_sender import send_notifications

_CJK = re.compile(r"[　-〿㐀-䶿一-鿿豈-﫿＀-￯]")


def _driver(driver_id: str, family: str) -> Driver:
    return Driver(driver_id=driver_id, given_name="X", family_name=family)


# --- 13. Date localization, independent of the process locale ---------------


def test_format_dt_localizes_names_from_catalog_not_process_locale():
    """zh-Hant renders Chinese weekday/month from the catalog, byte-identically
    regardless of the process `LC_TIME`/`LC_ALL`.

    WHY: `strftime("%a %b")` reads the *process-global* C locale — shared across
    all users, not per-request, and unsafe to mutate from async handlers. If a
    refactor reverted to `strftime` for names, the render under the "C" locale
    below would come back English ("Wed Jul") and these Chinese assertions would
    fail. That is exactly the trap this test guards.
    """
    dt = datetime(2026, 7, 29, 13, 5, tzinfo=UTC)  # a Wednesday, 13:05 UTC

    zh = format_dt(dt, "UTC", "zh-Hant")
    en = format_dt(dt, "UTC", "en")

    assert "7月" in zh and "29日" in zh and "週" in zh and "13:05" in zh
    assert "Jul" in en and "29" in en and "13:05" in en

    saved = locale.setlocale(locale.LC_ALL)
    try:
        locale.setlocale(locale.LC_ALL, "C")  # always available; English month names
        assert format_dt(dt, "UTC", "zh-Hant") == zh
        assert format_dt(dt, "UTC", "en") == en
    finally:
        locale.setlocale(locale.LC_ALL, saved)


# --- 14. Countdown localization --------------------------------------------


def test_countdown_units_and_phrases_render_per_language():
    """Unit suffixes and the boundary phrases come from the catalog per language.

    WHY: "in progress/finished", "< 1 minute" and the d/h/m suffixes are
    user-facing text like any other and must not be English-only.
    """
    now = datetime.now(UTC)

    future = now + timedelta(days=2, hours=3, minutes=30)
    assert format_countdown(future, "en") == "2d 3h"
    assert format_countdown(future, "zh-Hant") == "2 天 3 小時"

    soon = now + timedelta(seconds=40)
    assert format_countdown(soon, "en") == "< 1 minute"
    assert format_countdown(soon, "zh-Hant") == "不到 1 分鐘"

    past = now - timedelta(minutes=5)
    assert format_countdown(past, "en") == "In progress / finished"
    assert format_countdown(past, "zh-Hant") == "進行中／已結束"


# --- 15. Notification language (the Update-less path) -----------------------


async def test_notification_renders_in_recipient_language():
    """A reminder for a zh-Hant user is sent in Chinese, resolved via
    `get_user_language` (there is no `Update` on a JobQueue job).

    WHY: the background sender is the one user-facing surface that cannot call
    `resolve_context`. If it forgot `get_user_language`, every push would silently
    ship in English regardless of the recipient's choice.
    """
    sub = NotificationSubscription(
        id=1,
        telegram_id=777,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=datetime.now(UTC),
    )

    repo = AsyncMock()
    repo.get_pending_notifications = AsyncMock(return_value=[sub])
    repo.get_schedule = AsyncMock(return_value=[])  # race None -> push_no_race
    repo.get_user_language = AsyncMock(return_value="zh-Hant")
    repo.mark_notifications_sent = AsyncMock()
    repo.get_next_fire_at = AsyncMock(return_value=None)

    bot = AsyncMock()
    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])

    context = MagicMock()
    context.bot_data = {"repo": repo}
    context.bot = bot
    context.job_queue = jq

    await send_notifications(context)

    repo.get_user_language.assert_awaited_once_with(777)
    text = bot.send_message.await_args.kwargs["text"]
    assert _CJK.search(text), f"expected Chinese push text, got: {text!r}"
    assert "將在" in text and "分鐘" in text and "正賽" in text
    assert "starts in" not in text


async def test_notification_english_recipient_gets_english():
    """The mirror case — an en recipient gets the English push. WHY: proves the
    language is genuinely driven by `get_user_language`, not a constant."""
    sub = NotificationSubscription(
        id=2,
        telegram_id=888,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=15,
        fire_at=datetime.now(UTC),
    )

    repo = AsyncMock()
    repo.get_pending_notifications = AsyncMock(return_value=[sub])
    repo.get_schedule = AsyncMock(return_value=[])
    repo.get_user_language = AsyncMock(return_value="en")
    repo.mark_notifications_sent = AsyncMock()
    repo.get_next_fire_at = AsyncMock(return_value=None)

    bot = AsyncMock()
    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])

    context = MagicMock()
    context.bot_data = {"repo": repo}
    context.bot = bot
    context.job_queue = jq

    await send_notifications(context)

    text = bot.send_message.await_args.kwargs["text"]
    assert not _CJK.search(text)
    assert "starts in" in text and "Race" in text


# --- 16. Compare zh-leakage fixed ------------------------------------------


def test_compare_no_data_and_footnote_render_english_when_lang_en():
    """The formerly-hardcoded zh `/compare` strings now come from the catalog and
    render English under `lang="en"`.

    WHY: the original bug was three zh literals baked into feature code. This proves
    they were *relocated into the catalog and keyed by language*, not merely moved —
    an English user must see English here.
    """
    a, b = _driver("a", "Hamilton"), _driver("b", "Verstappen")

    en_empty = format_driver_comparison(a, b, {"has_data": False}, RenderContext(lang="en"))
    assert not _CJK.search(en_empty)
    assert "Not enough race data" in en_empty

    zh_empty = format_driver_comparison(a, b, {"has_data": False}, RenderContext(lang="zh-Hant"))
    assert _CJK.search(zh_empty)

    stats = {
        "has_data": True,
        "points": (100.0, 80.0),
        "quali": (5, 3),
        "race": (4, 4),
        "wins": (2, 1),
        "podiums": (6, 4),
        "dnfs": (1, 2),
    }
    en_table = format_driver_comparison(a, b, stats, RenderContext(lang="en"))
    assert "Points" in en_table and "incl. sprint" in en_table
    assert not _CJK.search(en_table)

    zh_table = format_driver_comparison(a, b, stats, RenderContext(lang="zh-Hant"))
    assert "積分" in zh_table and "含衝刺賽" in zh_table
