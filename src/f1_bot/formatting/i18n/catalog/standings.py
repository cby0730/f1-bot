"""/standings and /title.

``title.remaining`` carries both the counts and the already-pluralised English words.
Chinese has no plural inflection, so its template simply ignores the ``*_word``
placeholders — ``str.format`` tolerates unused keyword arguments.
"""

STANDINGS: dict[str, dict[str, str]] = {
    # --- /standings ----------------------------------------------------------
    "standings.wdc_header": {
        "en": "🏆 *{season} Driver Standings (WDC)*",
        "zh-Hant": "🏆 *{season} 車手積分榜 (WDC)*",
    },
    "standings.wcc_header": {
        "en": "🏭 *{season} Constructor Standings (WCC)*",
        "zh-Hant": "🏭 *{season} 車隊積分榜 (WCC)*",
    },
    "standings.driver_row": {
        "en": "{icon} {flag} {name} — *{points} pts* ({team})",
        "zh-Hant": "{icon} {flag} {name} — *{points} 分* ({team})",
    },
    "standings.constructor_row": {
        "en": "{icon} {flag} {name} — *{points} pts*",
        "zh-Hant": "{icon} {flag} {name} — *{points} 分*",
    },
    "standings.btn_drivers": {"en": "🏆 Drivers", "zh-Hant": "🏆 車手"},
    "standings.btn_constructors": {"en": "🏭 Constructors", "zh-Hant": "🏭 車隊"},
    # --- /title --------------------------------------------------------------
    "title.remaining": {
        "en": "📊 {races} {races_word} + {sprints} {sprints_word} left",
        "zh-Hant": "📊 尚餘 {races} 場正賽 + {sprints} 場衝刺賽",
    },
    "title.word_race": {"en": "race", "zh-Hant": "場正賽"},
    "title.word_races": {"en": "races", "zh-Hant": "場正賽"},
    "title.word_sprint": {"en": "sprint", "zh-Hant": "場衝刺賽"},
    "title.word_sprints": {"en": "sprints", "zh-Hant": "場衝刺賽"},
    "title.clinched": {
        "en": "🔒 *CLINCHED* — {name} is your {season} {champion}",
        "zh-Hant": "🔒 *已鎖定冠軍* — {name} 是 {season} 年{champion}",
    },
    "title.champion_wdc": {
        "en": "World Drivers' Champion",
        "zh-Hant": "世界車手冠軍",
    },
    "title.champion_wcc": {
        "en": "World Constructors' Champion",
        "zh-Hant": "世界車隊冠軍",
    },
    "title.magic_number": {
        "en": "_Magic number: {name} clinches with *{n}* more points._",
        "zh-Hant": "_魔術數字：{name} 再取得 *{n}* 分即可奪冠。_",
    },
}
