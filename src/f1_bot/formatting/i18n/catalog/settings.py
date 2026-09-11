"""/settings hub, timezone picker, and language picker.

Language *names* are deliberately identical across both catalogs: a user who has
accidentally switched to a language they cannot read must still recognise their own
language in the picker. Same reason the picker header is bilingual.
"""

SETTINGS: dict[str, dict[str, str]] = {
    # --- /settings hub -------------------------------------------------------
    "settings.hub": {
        "en": "⚙️ *Settings*\n\nChoose what to change:",
        "zh-Hant": "⚙️ *設定*\n\n請選擇要變更的項目：",
    },
    "settings.btn_timezone": {"en": "🌍 Timezone", "zh-Hant": "🌍 時區"},
    "settings.btn_language": {"en": "🌐 Language / 語言", "zh-Hant": "🌐 Language / 語言"},
    # --- /timezone -----------------------------------------------------------
    "settings.tz_unknown_short": {
        "en": "❌ Unknown timezone: `{tz}`\n\nPlease try /settings again.",
        "zh-Hant": "❌ 無法辨識的時區：`{tz}`\n\n請重新輸入 /settings。",
    },
    "settings.tz_picker": {
        "en": "🌍 *Set your timezone*\n\nCurrent: `{tz}`\n\nChoose your region:",
        "zh-Hant": "🌍 *設定時區*\n\n目前：`{tz}`\n\n請選擇地區：",
    },
    "settings.tz_picker_back": {
        "en": "🌍 *Set your timezone*\n\nChoose your region:",
        "zh-Hant": "🌍 *設定時區*\n\n請選擇地區：",
    },
    "settings.tz_city": {
        "en": "🌍 *{region}* — pick a city:",
        "zh-Hant": "🌍 *{region}* — 請選擇城市：",
    },
    "settings.tz_saved": {
        "en": "✅ Timezone set to *{tz}*\n\nRace times will now be shown in your local time.",
        "zh-Hant": "✅ 時區已設定為 *{tz}*\n\n比賽時間將以你的當地時間顯示。",
    },
    "settings.region_asia": {"en": "🌏 Asia", "zh-Hant": "🌏 亞洲"},
    "settings.region_europe": {"en": "🌍 Europe", "zh-Hant": "🌍 歐洲"},
    "settings.region_americas": {"en": "🌎 Americas", "zh-Hant": "🌎 美洲"},
    "settings.region_other": {"en": "🌐 UTC / Other", "zh-Hant": "🌐 UTC / 其他"},
    # --- language picker -----------------------------------------------------
    "settings.lang_picker": {
        "en": "🌐 *Language / 語言*\n\nCurrent: *{lang}*\n\nChoose your language:",
        "zh-Hant": "🌐 *Language / 語言*\n\n目前：*{lang}*\n\n請選擇語言：",
    },
    "settings.lang_saved": {
        "en": "✅ Language set to *{lang}*",
        "zh-Hant": "✅ 語言已設定為 *{lang}*",
    },
    "settings.lang_name_en": {"en": "English", "zh-Hant": "English"},
    "settings.lang_name_zh_hant": {"en": "繁體中文", "zh-Hant": "繁體中文"},
}
