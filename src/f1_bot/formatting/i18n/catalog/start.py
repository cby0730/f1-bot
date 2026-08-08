"""/start and /help.

Kept as whole blocks rather than per-line keys: this text is read as prose, and
splitting it would force translators to reassemble the layout from fragments.
"""

_HELP_EN = """
*F1 Bot Commands*

*Bot*
/start — Welcome message and command overview
/help — Show this command list

*Schedule*
/next — Next race overview + session filter buttons (FP1–Race)
/schedule — Full season race calendar
/countdown — Time remaining until the next race
/timezone — Set your timezone (e.g. /timezone Asia/Taipei)
/language — Set your language (English / 繁體中文)

*Standings*
/standings — WDC + WCC standings
/title — Title clinch analysis (magic number / champion)

*Results*
/results — Results overview + session filter (FP1–Race, round navigation)
/pitstops — Pit stop data (use ◀ ▶ buttons to navigate rounds)
/laps — Lap times with sector data (By-Lap / By-Driver view)

*Info*
/driver [name] — Driver profile
/circuit [name] — Circuit info

*Notifications*
/remind — Manage your session reminders
""".strip()

_HELP_ZH = """
*F1 Bot 指令列表*

*機器人*
/start — 歡迎訊息與指令總覽
/help — 顯示此指令列表

*賽程*
/next — 下一場比賽總覽 + 賽段篩選按鈕（FP1–正賽）
/schedule — 完整賽季行事曆
/countdown — 距離下一場比賽的倒數時間
/timezone — 設定你的時區（例如 /timezone Asia/Taipei）
/language — 設定你的語言（English / 繁體中文）

*積分榜*
/standings — 車手 + 車隊積分榜
/title — 冠軍鎖定分析（魔術數字 / 冠軍）

*成績*
/results — 成績總覽 + 賽段篩選（FP1–正賽，可切換站次）
/pitstops — 進站資料（使用 ◀ ▶ 按鈕切換站次）
/laps — 含分段時間的單圈資料（依圈次 / 依車手檢視）

*資訊*
/driver [姓名] — 車手檔案
/circuit [名稱] — 賽道資訊

*通知*
/remind — 管理你的賽段提醒
""".strip()

START: dict[str, dict[str, str]] = {
    "start.help": {"en": _HELP_EN, "zh-Hant": _HELP_ZH},
    "start.welcome_intro": {
        "en": (
            "Welcome to *F1 Bot*! Get Formula 1 race info, standings, and session results.\n\n"
            "Times are shown in *UTC* by default. Use /timezone to set your local timezone."
        ),
        "zh-Hant": (
            "歡迎使用 *F1 Bot*！在這裡取得一級方程式賽事資訊、積分榜與各賽段成績。\n\n"
            "時間預設以 *UTC* 顯示，請使用 /timezone 設定你的當地時區。"
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
