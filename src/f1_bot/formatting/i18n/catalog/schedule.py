"""/next, /schedule, /countdown, and the shared round-navigation widgets."""

SCHEDULE: dict[str, dict[str, str]] = {
    "schedule.next_race_header": {
        "en": "🏁 *Next Race: {name}*",
        "zh-Hant": "🏁 *下一場比賽：{name}*",
    },
    "schedule.location": {
        "en": "📍 {circuit}, {locality}, {country}",
        "zh-Hant": "📍 {circuit}，{locality}，{country}",
    },
    "schedule.race_line": {"en": "🗓 *Race:* {time}", "zh-Hant": "🗓 *正賽：* {time}"},
    "schedule.countdown_line": {
        "en": "⏱ *Countdown:* {countdown}",
        "zh-Hant": "⏱ *倒數：* {countdown}",
    },
    "schedule.sessions_header": {"en": "*Sessions:*", "zh-Hant": "*各節賽程：*"},
    "schedule.session_row": {
        "en": "  {icon} {label}: {time}",
        "zh-Hant": "  {icon} {label}：{time}",
    },
    "schedule.calendar_header": {
        "en": "📅 *{season} F1 Season Calendar*",
        "zh-Hant": "📅 *{season} F1 賽季行事曆*",
    },
    "schedule.calendar_row": {
        "en": "{marker} *R{round}* {name}\n       {time}",
        "zh-Hant": "{marker} *R{round}* {name}\n       {time}",
    },
    "schedule.countdown_msg": {
        "en": "⏱ *{name}*\nCountdown: *{countdown}*\nRace: {time}",
        "zh-Hant": "⏱ *{name}*\n倒數：*{countdown}*\n正賽：{time}",
    },
    "schedule.next_session_header": {
        "en": "{icon} *Next {label}: {name}*",
        "zh-Hant": "{icon} *下一節{label}：{name}*",
    },
    "schedule.next_session_time": {
        "en": "🗓 *{label}:* {time}",
        "zh-Hant": "🗓 *{label}：* {time}",
    },
    "schedule.no_upcoming_races": {
        "en": "No upcoming races",
        "zh-Hant": "沒有即將到來的比賽",
    },
    "schedule.no_upcoming_filtered": {
        "en": "No upcoming {session} sessions",
        "zh-Hant": "沒有即將到來的{session}",
    },
    "schedule.outdated_next": {
        "en": "This button is outdated. Use /next again.",
        "zh-Hant": "此按鈕已失效，請重新輸入 /next。",
    },
    # --- shared round navigation (pagination.py) -----------------------------
    "pagination.round_counter": {"en": "R{current}/{total}", "zh-Hant": "R{current}/{total}"},
    "pagination.round_picker_text": {
        "en": "🏁 *Select Round*\nCurrently viewing: R{round} — {name}",
        "zh-Hant": "🏁 *選擇站次*\n目前檢視：R{round} — {name}",
    },
    "pagination.unknown_race": {"en": "Unknown", "zh-Hant": "未知"},
}
