# 🏎️ F1 Telegram Bot

A full-featured and elegantly designed Telegram Bot for Formula 1, providing F1 schedules, countdowns, real-time session results, driver & constructor standings, lap timings (including sector times), pit stop logs, and customizable session reminders.

👉 **Try the Telegram Bot: [@F1_Infomation_bot](https://t.me/F1_Infomation_bot)**

---

## 📊 Data Sources

All F1 data provided by the bot is fetched from the following public APIs:

1. **[Jolpica F1 API (Ergast)](https://api.jolpi.ca/)**: For schedules, standings, race results, and basic driver/constructor metadata.
2. **[OpenF1 API](https://openf1.org/)**: For lap times, sector times, pit stop data, and precise session timings.

---

## ✨ Key Features

* **Schedules & Countdowns**: Check upcoming Grand Prix sessions (FP1, FP2, FP3, Qualifying, Sprint, and Race) and countdown to the next session.
* **Two-State Interactive UI**: `/next` and `/results` use a clean two-state button navigation layout, letting users switch between round overview and filtered sessions effortlessly.
* **Rich Race Data**:
  * **Standings**: Real-time driver standings (WDC) and constructor standings (WCC) toggles.
  * **Title Race**: See whether the championship is still up for grabs — the "magic number" of points the leader needs to make it mathematically impossible for anyone to catch them, or a 🔒 CLINCHED banner once the title is sealed, for both drivers and constructors.
  * **Lap Timings**: View lap times with precise sector-by-sector data, searchable either by lap number or by driver.
  * **Pit Stops**: See pit stop details for each driver per round, including stop count, lap number, and duration.
* **Local Timezone Support**: Automatically translates all session timings to your local timezone (e.g. `Asia/Taipei`) using `/timezone`.
* **Bilingual Interface (English / 繁體中文)**: Every message, button, reminder, and command-menu entry renders in your chosen language — switch any time with `/language`. Dates, countdowns, and session labels localize too, and reminders arrive in your language.
* **Personalized Notifications**: Subscribe to automated race alerts (15, 30, 60, or 180 minutes before sessions).

---

## 💬 Bot Commands

| Command | Description |
|---|---|
| `/start`, `/help` | Welcome message and command overview |
| `/next` | Next session overview with interactive filter buttons (FP1–Race) |
| `/schedule` | Full season race calendar |
| `/countdown` | Countdown to the next session or race |
| `/results` | Results overview with session filters and round navigation |
| `/pitstops` | Pit stop data per round with round navigation |
| `/laps` | Lap times with sector-by-sector details |
| `/standings` | Toggle between WDC and WCC standings |
| `/title` | See if the championship is decided yet — how many points the leader needs to seal it, or who has already clinched |
| `/driver [name]` | Search driver profiles (fuzzy-matching supported) |
| `/circuit [name]` | Search circuit information (fuzzy-matching supported) |
| `/timezone` | Set your local timezone (e.g., `/timezone Asia/Taipei`) |
| `/language` | Switch the interface language — English or 繁體中文 (e.g., `/language zh-Hant`) |
| `/remind` | View and manage your active session reminders |
