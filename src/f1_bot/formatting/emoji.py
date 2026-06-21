POSITION_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

COUNTRY_FLAGS: dict[str, str] = {
    "British": "🇬🇧",
    "German": "🇩🇪",
    "Dutch": "🇳🇱",
    "Spanish": "🇪🇸",
    "Finnish": "🇫🇮",
    "French": "🇫🇷",
    "Mexican": "🇲🇽",
    "Australian": "🇦🇺",
    "Canadian": "🇨🇦",
    "Japanese": "🇯🇵",
    "Chinese": "🇨🇳",
    "Thai": "🇹🇭",
    "Monegasque": "🇲🇨",
    "Italian": "🇮🇹",
    "Danish": "🇩🇰",
    "American": "🇺🇸",
    "Brazilian": "🇧🇷",
    "Argentine": "🇦🇷",
    "Austrian": "🇦🇹",
    "Swiss": "🇨🇭",
    "Belgian": "🇧🇪",
    "Polish": "🇵🇱",
    "Czech": "🇨🇿",
    "New Zealander": "🇳🇿",
    "Swedish": "🇸🇪",
    "Russian": "🇷🇺",
    "Korean": "🇰🇷",
    "Indian": "🇮🇳",
    "Venezuelan": "🇻🇪",
    "Colombian": "🇨🇴",
}

SESSION_ICONS = {
    "fp1": "🔧",
    "fp2": "🔧",
    "fp3": "🔧",
    "qualifying": "⏱",
    "sprint": "💨",
    "sprint_qualifying": "⏱",
    "race": "🏁",
}

FLAG_COLORS = {
    "GREEN": "🟢",
    "YELLOW": "🟡",
    "RED": "🔴",
    "BLUE": "🔵",
    "BLACK": "⬛",
    "CHEQUERED": "🏁",
    "SAFETY CAR": "🚗",
    "VIRTUAL SAFETY CAR": "🚙",
}


ISO_3_TO_2 = {
    "ARG": "AR",
    "AUS": "AU",
    "AUT": "AT",
    "BEL": "BE",
    "BRA": "BR",
    "CAN": "CA",
    "CHN": "CN",
    "COL": "CO",
    "CZE": "CZ",
    "DEN": "DK",
    "ESP": "ES",
    "FIN": "FI",
    "FRA": "FR",
    "GBR": "GB",
    "GER": "DE",
    "IND": "IN",
    "ITA": "IT",
    "JPN": "JP",
    "KOR": "KR",
    "MEX": "MX",
    "MON": "MC",
    "NED": "NL",
    "NZL": "NZ",
    "POL": "PL",
    "RUS": "RU",
    "SUI": "CH",
    "SWE": "SE",
    "THA": "TH",
    "USA": "US",
    "VEN": "VE",
    "EST": "EE",
    "ZAF": "ZA",
    "IDN": "ID",
    "ZWE": "ZW",
    "ISR": "IL",
    "TUR": "TR",
    "SMR": "SM",
    "ISL": "IS",
}


def country_code_to_flag(country_code_alpha3: str) -> str:
    """Convert a 3-letter country code to a country flag emoji."""
    if not country_code_alpha3:
        return "🏴"
    alpha2 = ISO_3_TO_2.get(country_code_alpha3.upper())
    if not alpha2:
        return "🏴"
    return "".join(chr(127397 + ord(c)) for c in alpha2.upper())


def pos_icon(position: int) -> str:
    return POSITION_MEDALS.get(position, f"P{position}")


def flag_icon(nationality: str) -> str:
    if not nationality:
        return "🏴"
    # If the input is already a flag emoji (regional indicators), return it
    if len(nationality) == 2 and all(127397 < ord(c) < 127500 for c in nationality):
        return nationality
    # Check manual lookup
    ret = COUNTRY_FLAGS.get(nationality)
    if ret:
        return ret
    # Check 3-letter code
    if len(nationality) == 3:
        return country_code_to_flag(nationality)
    return "🏴"


def session_icon(session_type: str) -> str:
    return SESSION_ICONS.get(session_type.lower(), "📅")


def flag_color(flag: str) -> str:
    return FLAG_COLORS.get(flag.upper() if flag else "", "🚩")
