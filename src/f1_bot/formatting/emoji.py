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


def pos_icon(position: int) -> str:
    return POSITION_MEDALS.get(position, f"P{position}")


def flag_icon(nationality: str) -> str:
    return COUNTRY_FLAGS.get(nationality, "🏴")


def session_icon(session_type: str) -> str:
    return SESSION_ICONS.get(session_type.lower(), "📅")


def flag_color(flag: str) -> str:
    return FLAG_COLORS.get(flag.upper() if flag else "", "🚩")
