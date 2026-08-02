"""/remind — subscription management plus the push message itself.

The push message is the only user-facing text rendered *outside* a request, so it
resolves language from the DB per recipient rather than from a RenderContext.
"""

NOTIFICATIONS: dict[str, dict[str, str]] = {
    "notifications.remind_btn": {"en": "🔔 Remind Me", "zh-Hant": "🔔 提醒我"},
    "notifications.pick_session": {
        "en": "🔔 *Select Session* — Round {round}\n\nWhich session do you want a reminder for?",
        "zh-Hant": "🔔 *選擇賽段* — 第 {round} 站\n\n你想要哪一節的提醒？",
    },
    "notifications.pick_timing": {
        "en": "🔔 *{session}* — Round {round}\n\nHow early do you want to be reminded?",
        "zh-Hant": "🔔 *{session}* — 第 {round} 站\n\n你想提前多久收到提醒？",
    },
    "notifications.none_active": {
        "en": "🔔 You have no active reminders.\n\nUse /next and tap 🔔 to set one.",
        "zh-Hant": "🔔 你目前沒有任何提醒。\n\n請使用 /next 並點擊 🔔 來設定。",
    },
    "notifications.round_header": {
        "en": "🔔 *R{round} — {name}*",
        "zh-Hant": "🔔 *R{round} — {name}*",
    },
    "notifications.round_btn": {"en": "Round {round}", "zh-Hant": "第 {round} 站"},
    "notifications.delete_btn": {
        "en": "🗑 {session} — {timing}",
        "zh-Hant": "🗑 {session} — {timing}",
    },
    "notifications.list_header": {
        "en": "🔔 *Your Active Reminders*",
        "zh-Hant": "🔔 *你的提醒清單*",
    },
    "notifications.round_count_btn": {
        "en": "🔔 R{round} — {name} ({count})",
        "zh-Hant": "🔔 R{round} — {name} ({count})",
    },
    "notifications.clear_all_btn": {"en": "🗑 Clear All", "zh-Hant": "🗑 全部清除"},
    "notifications.no_sessions": {"en": "No sessions available", "zh-Hant": "沒有可用的賽段"},
    "notifications.removed": {
        "en": "🔕 Reminder removed: {timing}",
        "zh-Hant": "🔕 已移除提醒：{timing}",
    },
    "notifications.limit_reached": {
        "en": "⚠️ Limit reached ({max}). Remove some with /remind first.",
        "zh-Hant": "⚠️ 已達上限（{max} 筆），請先用 /remind 移除部分提醒。",
    },
    "notifications.session_not_found": {"en": "Session not found", "zh-Hant": "找不到該賽段"},
    "notifications.set": {
        "en": "🔔 Reminder set: {timing} before",
        "zh-Hant": "🔔 已設定提醒：賽前 {timing}",
    },
    "notifications.not_found": {"en": "Reminder not found", "zh-Hant": "找不到該提醒"},
    "notifications.removed_toast": {"en": "🗑 Reminder removed", "zh-Hant": "🗑 已移除提醒"},
    "notifications.confirm_yes": {"en": "✅ Yes, clear all", "zh-Hant": "✅ 是，全部清除"},
    "notifications.confirm_no": {"en": "❌ Cancel", "zh-Hant": "❌ 取消"},
    "notifications.confirm_text": {
        "en": "🗑 *Are you sure?*\n\nThis will remove all your active reminders.",
        "zh-Hant": "🗑 *確定嗎？*\n\n這將移除你所有的提醒。",
    },
    "notifications.cleared_toast": {
        "en": "Cleared {count} reminder(s)",
        "zh-Hant": "已清除 {count} 筆提醒",
    },
    "notifications.cleared_text": {
        "en": "🔔 All reminders cleared.\n\nUse /next and tap 🔔 to set new ones.",
        "zh-Hant": "🔔 已清除所有提醒。\n\n請使用 /next 並點擊 🔔 重新設定。",
    },
    "notifications.cancelled": {"en": "Cancelled", "zh-Hant": "已取消"},
    # --- timing presets ------------------------------------------------------
    "notifications.timing_15": {"en": "15min", "zh-Hant": "15 分鐘"},
    "notifications.timing_30": {"en": "30min", "zh-Hant": "30 分鐘"},
    "notifications.timing_60": {"en": "1hr", "zh-Hant": "1 小時"},
    "notifications.timing_180": {"en": "3hr", "zh-Hant": "3 小時"},
    # --- the push message ----------------------------------------------------
    "notifications.push_with_race": {
        "en": "🔔 *{name}* — {session} starts in *{minutes} minutes*!",
        "zh-Hant": "🔔 *{name}* — {session}將在 *{minutes} 分鐘*後開始！",
    },
    "notifications.push_no_race": {
        "en": "🔔 {session} starts in *{minutes} minutes*!",
        "zh-Hant": "🔔 {session}將在 *{minutes} 分鐘*後開始！",
    },
}
