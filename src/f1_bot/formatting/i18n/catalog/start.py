"""/start welcome copy.

Kept as whole blocks rather than per-line keys: this text is read as prose, and
splitting it would force translators to reassemble the layout from fragments.

The welcome is a short intro plus data-sources and GitHub-star lines. Commands
are offered as an eight-button keyboard, not a slash list — see ``start.btn_*``.
"""

START: dict[str, dict[str, str]] = {
    "start.welcome_intro": {
        "en": (
            "Welcome to *F1 Bot*! Get Formula 1 race info, standings, and session results.\n\n"
            "Times are shown in *UTC* by default. Use the Settings / 設定 button below "
            "to set your timezone and language."
        ),
        "zh-Hant": (
            "歡迎使用 *F1 Bot*！在這裡取得一級方程式賽事資訊、積分榜與各賽段成績。\n\n"
            "時間預設以 *UTC* 顯示，請用下方 Settings / 設定 調整時區與語言。"
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
    "start.btn_next": {"en": "🏁 Next", "zh-Hant": "🏁 下一場"},
    "start.btn_schedule": {"en": "📅 Schedule", "zh-Hant": "📅 賽曆"},
    "start.btn_results": {"en": "📊 Results", "zh-Hant": "📊 成績"},
    "start.btn_standings": {"en": "🏆 Standings", "zh-Hant": "🏆 積分榜"},
    "start.btn_driver": {"en": "🏎 Driver", "zh-Hant": "🏎 車手"},
    "start.btn_circuit": {"en": "📍 Circuit", "zh-Hant": "📍 賽道"},
    "start.btn_remind": {"en": "🔔 Remind", "zh-Hant": "🔔 提醒"},
    "start.btn_settings": {"en": "⚙️ Settings / 設定", "zh-Hant": "⚙️ Settings / 設定"},
}
