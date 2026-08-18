"""Descriptions for Telegram's `set_my_commands` menu.

``COMMAND_ORDER`` is the display order of the menu; ``main.py`` walks it once per
shipped language and calls `set_my_commands(..., language_code=...)`. This is the
one localisation mechanism that is Telegram-native — a future LINE adapter has no
equivalent, so it stays in the platform layer and only the *text* lives here.

Hidden aliases (`/help`, `/countdown`, `/title`, `/timezone`, `/language`,
`/compare`, `/pitstops`, `/laps`) stay registered as ``CommandHandler``s but are
not listed here — Telegram silently ignores a mismatched menu length, so this
tuple is the source of truth for the visible 9.
"""

COMMAND_ORDER: tuple[str, ...] = (
    "start",
    "next",
    "schedule",
    "results",
    "standings",
    "driver",
    "circuit",
    "remind",
    "settings",
)

COMMANDS: dict[str, dict[str, str]] = {
    "commands.start": {
        "en": "Welcome message and command overview",
        "zh-Hant": "歡迎訊息與指令總覽",
    },
    "commands.next": {
        "en": "Next race — session filter buttons",
        "zh-Hant": "下一場比賽 — 賽段篩選按鈕",
    },
    "commands.schedule": {"en": "Full season race calendar", "zh-Hant": "完整賽季行事曆"},
    "commands.results": {
        "en": "Results, pit stops, and lap times",
        "zh-Hant": "成績、進站與單圈時間",
    },
    "commands.standings": {"en": "WDC + WCC standings", "zh-Hant": "車手 + 車隊積分榜"},
    "commands.driver": {"en": "Driver profile", "zh-Hant": "車手檔案"},
    "commands.circuit": {"en": "Circuit info", "zh-Hant": "賽道資訊"},
    "commands.remind": {"en": "Manage notification reminders", "zh-Hant": "管理提醒通知"},
    "commands.settings": {"en": "Timezone and language", "zh-Hant": "時區與語言"},
}
