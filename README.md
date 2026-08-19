# 🏎️ F1 Telegram Bot

A full-featured and elegantly designed Telegram Bot for Formula 1, providing F1 schedules, countdowns, real-time session results, driver & constructor standings, lap timings (including sector times), pit stop logs, and customizable session reminders.

👉 **Try the Telegram Bot: [@F1_Infomation_bot](https://t.me/F1_Infomation_bot)**

![Bot demo](docs/demo.gif)

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
* **Title Race**: `/standings` shows whether the championship is still up for grabs — the "magic number" of points the leader needs, or a 🔒 CLINCHED banner once the title is sealed, for both drivers and constructors.
* **Lap Timings**: Personal-best sector and lap times per driver, with a DNF tag when the race result is unclassified.
* **Pit Stops**: Pit stop details for each driver per round, including stop count, lap number, and duration — nested under `/results`.
* **Local Timezone Support**: Session timings render in the timezone you pick from `/settings` (region, then city).
* **Bilingual Interface (English / 繁體中文)**: Every message, button, reminder, and command-menu entry renders in your chosen language — switch any time from the `/settings` picker. Dates, countdowns, and session labels localize too, and reminders arrive in your language.
* **Personalized Notifications**: Subscribe to automated race alerts (15, 30, 60, or 180 minutes before sessions).

---

## 💬 Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and command overview |
| `/next` | Next session overview with interactive filter buttons (FP1–Race) |
| `/schedule` | Full season race calendar |
| `/results` | Results overview with session filters, pit stops, lap times, and round navigation |
| `/standings` | Toggle between WDC and WCC standings, including title-clinch status |
| `/driver` | Driver profiles — pick from the current-season list; Compare from the profile |
| `/circuit` | Circuit info — pick from the season calendar |
| `/remind` | View and manage your active session reminders |
| `/settings` | Timezone and language pickers |
