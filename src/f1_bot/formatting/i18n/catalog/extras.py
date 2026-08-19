"""/driver, /circuit and /compare."""

EXTRAS: dict[str, dict[str, str]] = {
    # --- pickers -------------------------------------------------------------
    "extras.select_driver": {"en": "🏎 Select a driver:", "zh-Hant": "🏎 請選擇車手："},
    "extras.select_circuit": {"en": "📍 Select a circuit:", "zh-Hant": "📍 請選擇賽道："},
    "extras.driver_not_found": {"en": "Driver not found", "zh-Hant": "找不到車手"},
    "extras.circuit_not_found": {"en": "Circuit not found", "zh-Hant": "找不到賽道"},
    # --- driver profile ------------------------------------------------------
    "extras.profile_header": {
        "en": "🏎 *{name}*{code}  {flag}",
        "zh-Hant": "🏎 *{name}*{code}  {flag}",
    },
    "extras.profile_number_team": {
        "en": "Number: *{number}*  |  Team: *{team}*",
        "zh-Hant": "車號：*{number}*  |  車隊：*{team}*",
    },
    "extras.profile_nationality_dob": {
        "en": "Nationality: {nationality}  |  DOB: {dob}",
        "zh-Hant": "國籍：{nationality}  |  生日：{dob}",
    },
    "extras.profile_standing": {
        "en": "\n📊 *{position}th* in WDC — *{points} pts* ({wins} wins)",
        "zh-Hant": "\n📊 車手榜第 *{position}* 名 — *{points} 分*（{wins} 勝）",
    },
    "extras.wikipedia": {"en": "\n[Wikipedia]({url})", "zh-Hant": "\n[維基百科]({url})"},
    # --- circuit info --------------------------------------------------------
    "extras.circuit_header": {"en": "🏁 *{name}*  {flag}", "zh-Hant": "🏁 *{name}*  {flag}"},
    "extras.circuit_location": {
        "en": "{locality}, {country}{coords}",
        "zh-Hant": "{locality}，{country}{coords}",
    },
    "extras.circuit_coords": {"en": "\n📍 {lat}, {lng}", "zh-Hant": "\n📍 {lat}, {lng}"},
    "extras.recent_winners": {"en": "\n*Recent winners:*", "zh-Hant": "\n*近期場次：*"},
    "extras.recent_row": {"en": "  {season}: {name}", "zh-Hant": "  {season}：{name}"},
    # --- /compare ------------------------------------------------------------
    "extras.compare_with": {"en": "🆚 Compare with…", "zh-Hant": "🆚 與其他車手比較"},
    "compare.pick_a": {"en": "🆚 Select driver *A*:", "zh-Hant": "🆚 請選擇車手 *A*："},
    "compare.pick_b": {"en": "🆚 Select driver *B*:", "zh-Hant": "🆚 請選擇車手 *B*："},
    "compare.restart": {"en": "🔙 Compare again", "zh-Hant": "🔙 重新比較"},
    "compare.swap_opponent": {"en": "🔄 Swap opponent", "zh-Hant": "🔄 更換對手"},
    "compare.header": {"en": "🆚 *{a}*  vs  *{b}*", "zh-Hant": "🆚 *{a}*  對決  *{b}*"},
    "compare.no_data": {
        "en": "Not enough race data this season yet — try again after the first race.",
        "zh-Hant": "本賽季尚無足夠比賽資料可供對決，請待首場比賽後再試",
    },
    "compare.footnote": {"en": "* incl. sprint", "zh-Hant": "* 含衝刺賽"},
    "compare.row_points": {"en": "Points", "zh-Hant": "積分"},
    "compare.row_quali": {"en": "Quali H2H", "zh-Hant": "排位對決"},
    "compare.row_race": {"en": "Race+Spr", "zh-Hant": "正賽+衝刺"},
    "compare.row_wins": {"en": "Wins", "zh-Hant": "勝場"},
    "compare.row_podiums": {"en": "Podiums", "zh-Hant": "頒獎台"},
    "compare.row_dnfs": {"en": "DNFs", "zh-Hant": "退賽"},
}
