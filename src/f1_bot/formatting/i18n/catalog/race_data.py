"""/pitstops and /laps.

The ``laps_table_header`` entry sits inside a monospace block, so the Chinese
variant is padded to the *same display width* as the English one: 車手 occupies
four terminal columns and replaces six ASCII columns, with two spaces making up
the difference.
"""

RACE_DATA: dict[str, dict[str, str]] = {
    # --- pit stops -----------------------------------------------------------
    "race_data.pitstops_header": {
        "en": "🔧 *{title} — Pit Stops*",
        "zh-Hant": "🔧 *{title} — 進站紀錄*",
    },
    "race_data.pitstop_row": {"en": "🏎 *{driver}*: {stops}", "zh-Hant": "🏎 *{driver}*：{stops}"},
    "race_data.pitstop_lap": {"en": "Lap {lap}: {duration}", "zh-Hant": "第 {lap} 圈：{duration}"},
    # --- laps: personal-best table ------------------------------------------
    "race_data.laps_summary_header": {
        "en": "⏱ *{title} — Lap Times*",
        "zh-Hant": "⏱ *{title} — 單圈時間*",
    },
    "race_data.laps_table_header": {
        "en": "`Driver  S1   │ S2   │ S3   │ Best     `",
        "zh-Hant": "`車手    S1   │ S2   │ S3   │ Best     `",
    },
    "race_data.dnf_tag": {"en": "DNF", "zh-Hant": "DNF"},
    "race_data.note_timing": {
        "en": "\n*Note: Timing data from live feeds may occasionally be incomplete.*",
        "zh-Hant": "\n*註：即時計時資料偶爾可能不完整。*",
    },
}
