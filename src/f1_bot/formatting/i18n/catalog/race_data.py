"""/pitstops and /laps.

The two ``*_table_header`` entries sit inside a monospace block, so the Chinese
variants are padded to the *same display width* as the English ones: 車手 and 圈數
each occupy two terminal columns per glyph, so they replace 6 and 3 ASCII columns
with 4, and the difference is made up with spaces.
"""

RACE_DATA: dict[str, dict[str, str]] = {
    # --- pit stops -----------------------------------------------------------
    "race_data.pitstops_header": {
        "en": "🔧 *{title} — Pit Stops*",
        "zh-Hant": "🔧 *{title} — 進站紀錄*",
    },
    "race_data.pitstop_row": {"en": "🏎 *{driver}*: {stops}", "zh-Hant": "🏎 *{driver}*：{stops}"},
    "race_data.pitstop_lap": {"en": "Lap {lap}: {duration}", "zh-Hant": "第 {lap} 圈：{duration}"},
    # --- laps: summary -------------------------------------------------------
    "race_data.laps_summary_header": {
        "en": "⏱ *{title} — Lap Times Summary*",
        "zh-Hant": "⏱ *{title} — 單圈時間總覽*",
    },
    "race_data.laps_summary_row": {
        "en": "🏎 *{label}*: Best `{best}` | Avg `{avg}` | {count} laps",
        "zh-Hant": "🏎 *{label}*：最快 `{best}` | 平均 `{avg}` | {count} 圈",
    },
    # --- laps: by lap --------------------------------------------------------
    "race_data.lap_header": {
        "en": "⏱ *{title} — Lap {lap}/{total}*",
        "zh-Hant": "⏱ *{title} — 第 {lap}/{total} 圈*",
    },
    "race_data.lap_table_header": {
        "en": "`     Driver  S1   │ S2   │ S3   │ Lap     `",
        "zh-Hant": "`     車手    S1   │ S2   │ S3   │ Lap     `",
    },
    "race_data.no_lap_entries": {"en": "_No data for this lap_", "zh-Hant": "_本圈無資料_"},
    "race_data.note_lap1": {
        "en": "\n*Note: Lap 1 is the standing start lap; timing data may be incomplete.*",
        "zh-Hant": "\n*註：第 1 圈為起跑圈，計時資料可能不完整。*",
    },
    "race_data.note_timing": {
        "en": "\n*Note: Timing data from live feeds may occasionally be incomplete.*",
        "zh-Hant": "\n*註：即時計時資料偶爾可能不完整。*",
    },
    # --- laps: by driver -----------------------------------------------------
    "race_data.driver_laps_header": {
        "en": "⏱ *{title} — {label} Lap Times*",
        "zh-Hant": "⏱ *{title} — {label} 單圈時間*",
    },
    "race_data.driver_table_header": {
        "en": "`Lap   S1   │ S2   │ S3   │ Lap     `",
        "zh-Hant": "`圈數  S1   │ S2   │ S3   │ Lap     `",
    },
    "race_data.driver_lap_row": {
        "en": "Lap {lap}: `{time}`",
        "zh-Hant": "第 {lap} 圈：`{time}`",
    },
    "race_data.page_footer": {
        "en": "\n_Page {page}/{pages} — {total} laps total_",
        "zh-Hant": "\n_第 {page}/{pages} 頁 — 共 {total} 圈_",
    },
    "race_data.driver_picker_header": {
        "en": "⏱ *{title} — Select a Driver*\n\nTap a driver code to view their lap times:",
        "zh-Hant": "⏱ *{title} — 選擇車手*\n\n點選車手代號以查看其單圈時間：",
    },
    # --- buttons / toasts ----------------------------------------------------
    "race_data.btn_by_lap": {"en": "📊 By Lap", "zh-Hant": "📊 依圈次"},
    "race_data.btn_by_driver": {"en": "🏎 By Driver", "zh-Hant": "🏎 依車手"},
    "race_data.btn_summary": {"en": "🔙 Summary", "zh-Hant": "🔙 總覽"},
    "race_data.btn_drivers": {"en": "🔙 Drivers", "zh-Hant": "🔙 車手"},
    "race_data.btn_lap_counter": {
        "en": "Lap {current}/{total}",
        "zh-Hant": "第 {current}/{total} 圈",
    },
    "race_data.btn_page_range": {
        "en": "{start}–{end} of {total}",
        "zh-Hant": "{start}–{end} / 共 {total}",
    },
    "race_data.no_lap_data": {"en": "No lap data available", "zh-Hant": "無單圈資料"},
    "race_data.no_driver_data": {
        "en": "No data for driver {driver}",
        "zh-Hant": "找不到車手 {driver} 的資料",
    },
}
