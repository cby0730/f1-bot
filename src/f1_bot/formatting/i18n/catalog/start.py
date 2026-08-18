"""/start welcome copy.

Kept as whole blocks rather than per-line keys: this text is read as prose, and
splitting it would force translators to reassemble the layout from fragments.

``start.help`` lists the *visible* menu (``COMMAND_ORDER``), not hidden aliases.
"""

_HELP_EN = """
*What I can do*

/start — Welcome and this list
/next — Next race weekend (sessions + countdown)
/schedule — Full season calendar
/results — Session results, pit stops, and lap times
/standings — Championship standings and title race
/driver — Driver profile
/circuit — Circuit info
/remind — Session reminders
/settings — Timezone and language
""".strip()

_HELP_ZH = """
*我能做什麼*

/start — 歡迎訊息與本列表
/next — 下一場比賽週末（賽段 + 倒數）
/schedule — 完整賽季行事曆
/results — 各賽段成績、進站與單圈時間
/standings — 積分榜與冠軍鎖定
/driver — 車手檔案
/circuit — 賽道資訊
/remind — 賽段提醒
/settings — 時區與語言
""".strip()

START: dict[str, dict[str, str]] = {
    "start.help": {"en": _HELP_EN, "zh-Hant": _HELP_ZH},
    "start.welcome_intro": {
        "en": (
            "Welcome to *F1 Bot*! Get Formula 1 race info, standings, and session results.\n\n"
            "Times are shown in *UTC* by default. Use /settings to set your timezone and language."
        ),
        "zh-Hant": (
            "歡迎使用 *F1 Bot*！在這裡取得一級方程式賽事資訊、積分榜與各賽段成績。\n\n"
            "時間預設以 *UTC* 顯示，請使用 /settings 設定你的時區與語言。"
        ),
    },
    "start.data_sources": {
        "en": (
            "📊 *Data Sources*:\n"
            "• [Jolpica F1 API](https://github.com/jolpica/jolpica-f1) (Ergast)\n"
            "• [OpenF1 API](https://github.com/br-g/openf1)"
        ),
        "zh-Hant": (
            "📊 *資料來源*：\n"
            "• [Jolpica F1 API](https://github.com/jolpica/jolpica-f1) (Ergast)\n"
            "• [OpenF1 API](https://github.com/br-g/openf1)"
        ),
    },
    "start.support": {
        "en": (
            "⭐ *Support this project*:\n"
            "If you like this bot, please give it a star on "
            "[GitHub](https://github.com/cby0730/f1-bot)!"
        ),
        "zh-Hant": (
            "⭐ *支持這個專案*：\n"
            "如果你喜歡這個機器人，歡迎到 "
            "[GitHub](https://github.com/cby0730/f1-bot) 給我們一顆星！"
        ),
    },
}
