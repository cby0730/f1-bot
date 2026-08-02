"""Cross-domain strings: toasts, nouns, session labels.

``common.noun_*`` entries exist so ``no_data_message`` can interpolate a *translated*
fragment. Interpolating a raw English word into a Chinese sentence is the classic
i18n leak, so the noun itself is a catalog key.
"""

COMMON: dict[str, dict[str, str]] = {
    # --- buttons -------------------------------------------------------------
    "common.back": {"en": "🔙 Back", "zh-Hant": "🔙 返回"},
    "common.back_prev": {"en": "« Back", "zh-Hant": "« 返回"},
    # --- toasts / alerts -----------------------------------------------------
    "common.invalid_selection": {"en": "Invalid selection", "zh-Hant": "無效的選擇"},
    "common.database_unavailable": {"en": "Database unavailable", "zh-Hant": "資料庫無法使用"},
    "common.error_occurred": {"en": "An error occurred", "zh-Hant": "發生錯誤"},
    "common.failed_to_load": {"en": "Failed to load data", "zh-Hant": "資料載入失敗"},
    "common.schedule_unavailable": {"en": "Schedule unavailable", "zh-Hant": "無法取得賽程"},
    "common.round_not_found": {"en": "Round not found", "zh-Hant": "找不到該站"},
    "common.race_not_found": {"en": "Race not found", "zh-Hant": "找不到該場比賽"},
    "common.no_rounds_available": {"en": "No rounds available", "zh-Hant": "沒有可選的站次"},
    "common.generic_error": {
        "en": "Something went wrong. Please try again in a moment.",
        "zh-Hant": "發生了一些問題，請稍後再試。",
    },
    # --- "no data yet" -------------------------------------------------------
    "common.no_data": {
        "en": "⚠️ No {what} available yet. Try again after the next refresh.",
        "zh-Hant": "⚠️ 目前尚無{what}，請於下次更新後再試。",
    },
    "common.noun_data": {"en": "data", "zh-Hant": "資料"},
    "common.noun_schedule": {"en": "schedule", "zh-Hant": "賽程資料"},
    "common.noun_results": {"en": "results", "zh-Hant": "成績資料"},
    "common.noun_standings": {"en": "standings", "zh-Hant": "積分榜資料"},
    "common.noun_pitstops": {"en": "pit stop data", "zh-Hant": "進站資料"},
    "common.noun_laps": {"en": "lap data", "zh-Hant": "單圈資料"},
    "common.noun_driver_list": {"en": "driver list", "zh-Hant": "車手列表資料"},
    "common.noun_circuit_list": {"en": "circuit list", "zh-Hant": "賽道列表資料"},
    "common.noun_upcoming_race": {"en": "upcoming race", "zh-Hant": "即將到來的比賽資料"},
    "common.noun_session_results": {
        "en": "{session} results",
        "zh-Hant": "{session}成績資料",
    },
    # --- shared fragments ----------------------------------------------------
    "common.tbd": {"en": "TBD", "zh-Hant": "待定"},
    "common.round_of_season": {
        "en": "🏎 Round {round} of the {season} season",
        "zh-Hant": "🏎 {season} 賽季第 {round} 站",
    },
    "common.round_short": {"en": "Round {round}", "zh-Hant": "第 {round} 站"},
    "common.race_fallback_title": {"en": "Race", "zh-Hant": "比賽"},
    # --- session labels (full form, used in headers) -------------------------
    "session.fp1": {"en": "FP1", "zh-Hant": "自由練習一"},
    "session.fp2": {"en": "FP2", "zh-Hant": "自由練習二"},
    "session.fp3": {"en": "FP3", "zh-Hant": "自由練習三"},
    "session.sprint_qualifying": {"en": "Sprint Qualifying", "zh-Hant": "衝刺排位賽"},
    "session.sprint": {"en": "Sprint", "zh-Hant": "衝刺賽"},
    "session.qualifying": {"en": "Qualifying", "zh-Hant": "排位賽"},
    "session.race": {"en": "Race", "zh-Hant": "正賽"},
    "session.all": {"en": "All", "zh-Hant": "全部"},
    # --- session labels (short form, used in the /next session list) ---------
    "session.short.fp1": {"en": "FP1", "zh-Hant": "自由練習一"},
    "session.short.fp2": {"en": "FP2", "zh-Hant": "自由練習二"},
    "session.short.fp3": {"en": "FP3", "zh-Hant": "自由練習三"},
    "session.short.sprint_qualifying": {"en": "Sprint Quali", "zh-Hant": "衝刺排位"},
    "session.short.sprint": {"en": "Sprint", "zh-Hant": "衝刺賽"},
    "session.short.qualifying": {"en": "Quali", "zh-Hant": "排位賽"},
    "session.short.race": {"en": "Race", "zh-Hant": "正賽"},
    # --- session labels (button form) ----------------------------------------
    # A third, even narrower vocabulary: these sit four-to-a-row in an inline
    # keyboard, so English abbreviates hard (Q, SQ, SPR). Chinese does not need the
    # same squeeze — two glyphs already fit — so it uses readable words instead of
    # transliterated initials.
    "session.btn.fp1": {"en": "FP1", "zh-Hant": "FP1"},
    "session.btn.fp2": {"en": "FP2", "zh-Hant": "FP2"},
    "session.btn.fp3": {"en": "FP3", "zh-Hant": "FP3"},
    "session.btn.qualifying": {"en": "Q", "zh-Hant": "排位"},
    "session.btn.sprint_qualifying": {"en": "SQ", "zh-Hant": "衝排"},
    "session.btn.sprint": {"en": "SPR", "zh-Hant": "衝刺"},
    "session.btn.race": {"en": "Race", "zh-Hant": "正賽"},
    "session.btn.all": {"en": "All", "zh-Hant": "全部"},
}
