"""/results — session result headers, rows and the 4096-char truncation notes."""

RESULTS: dict[str, dict[str, str]] = {
    "results.race_header": {
        "en": "🏁 *{name} — Race Result*",
        "zh-Hant": "🏁 *{name} — 正賽成績*",
    },
    "results.qualifying_header": {
        "en": "⏱ *{name} — Qualifying*",
        "zh-Hant": "⏱ *{name} — 排位賽*",
    },
    "results.sprint_header": {"en": "💨 *{name} — Sprint*", "zh-Hant": "💨 *{name} — 衝刺賽*"},
    "results.session_header": {
        "en": "{icon} *{name} — {label} Result*",
        "zh-Hant": "{icon} *{name} — {label}成績*",
    },
    "results.row": {
        "en": "{icon} {flag} {name}{extra} — {value}",
        "zh-Hant": "{icon} {flag} {name}{extra} — {value}",
    },
    "results.no_session_data": {
        "en": "No {label} data yet this season",
        "zh-Hant": "本賽季尚無{label}資料",
    },
    "results.outdated": {
        "en": "This button is outdated. Use /results again.",
        "zh-Hant": "此按鈕已失效，請重新輸入 /results。",
    },
    "results.truncated_practice": {
        "en": (
            "\n\n⚠️ *Practice results (FP1/FP2/FP3) omitted to fit Telegram character "
            "limits. Please use the buttons above to view them.*"
        ),
        "zh-Hant": (
            "\n\n⚠️ *為符合 Telegram 字數限制，已省略自由練習 (FP1/FP2/FP3) 成績，"
            "請使用上方按鈕查看。*"
        ),
    },
    "results.truncated_top10": {
        "en": (
            "\n\n⚠️ *Practice results omitted and remaining results truncated to top 10 "
            "to fit Telegram character limits.*"
        ),
        "zh-Hant": (
            "\n\n⚠️ *為符合 Telegram 字數限制，已省略自由練習成績，其餘成績僅顯示前 10 名。*"
        ),
    },
}
