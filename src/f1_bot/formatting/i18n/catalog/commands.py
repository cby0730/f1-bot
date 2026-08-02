"""Descriptions for Telegram's `set_my_commands` menu.

``COMMAND_ORDER`` is the display order of the menu; ``main.py`` walks it once per
shipped language and calls `set_my_commands(..., language_code=...)`. This is the
one localisation mechanism that is Telegram-native — a future LINE adapter has no
equivalent, so it stays in the platform layer and only the *text* lives here.
"""

COMMAND_ORDER: tuple[str, ...] = (
    "start",
    "help",
    "next",
    "schedule",
    "countdown",
    "timezone",
    "language",
    "standings",
    "title",
    "results",
    "pitstops",
    "laps",
    "driver",
    "circuit",
    "compare",
    "remind",
)

COMMANDS: dict[str, dict[str, str]] = {
    "commands.start": {
        "en": "Welcome message and command overview",
        "zh-Hant": "歡迎訊息與指令總覽",
    },
    "commands.help": {"en": "Show command list", "zh-Hant": "顯示指令列表"},
    "commands.next": {
        "en": "Next race — session filter buttons",
        "zh-Hant": "下一場比賽 — 賽段篩選按鈕",
    },
    "commands.schedule": {"en": "Full season race calendar", "zh-Hant": "完整賽季行事曆"},
    "commands.countdown": {
        "en": "Time remaining until the next race",
        "zh-Hant": "距離下一場比賽的倒數時間",
    },
    "commands.timezone": {"en": "Set your timezone", "zh-Hant": "設定你的時區"},
    "commands.language": {"en": "Set your language", "zh-Hant": "設定你的語言"},
    "commands.standings": {"en": "WDC + WCC standings", "zh-Hant": "車手 + 車隊積分榜"},
    "commands.title": {
        "en": "WDC + WCC title clinch analysis",
        "zh-Hant": "車手 + 車隊冠軍鎖定分析",
    },
    "commands.results": {
        "en": "Results — session filter + round navigation",
        "zh-Hant": "成績 — 賽段篩選 + 站次切換",
    },
    "commands.pitstops": {
        "en": "Pit stop data with round navigation",
        "zh-Hant": "進站資料，可切換站次",
    },
    "commands.laps": {"en": "Lap times with sector data", "zh-Hant": "含分段時間的單圈資料"},
    "commands.driver": {"en": "Driver profile", "zh-Hant": "車手檔案"},
    "commands.circuit": {"en": "Circuit info", "zh-Hant": "賽道資訊"},
    "commands.compare": {
        "en": "Head-to-head compare two drivers",
        "zh-Hant": "兩位車手的正面對決比較",
    },
    "commands.remind": {"en": "Manage notification reminders", "zh-Hant": "管理提醒通知"},
}
