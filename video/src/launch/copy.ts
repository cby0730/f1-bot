/** Approved launch-film copy. UI strings match the bot catalog. */

export const raceName = "Singapore Grand Prix";
export const localTime = "8:00 PM";
export const lockTime = "8:30";
export const lockPeriod = "PM";
export const lockDate = "Saturday, September 20";

export const hook = {
  headline: "Your Pocket pit wall",
  support: "Built for Telegram",
  sub: "For people who already live here.",
};

export const start = {
  label: "IN CHAT",
  headline: "Eight taps.",
};

export const startButtons = [
  "🏁 Next",
  "📅 Schedule",
  "📊 Results",
  "🏆 Standings",
  "🏎 Driver",
  "📍 Circuit",
  "🔔 Remind",
  "⚙️ Settings / 設定",
] as const;

export const next = {
  label: "YOUR CLOCK",
  headline: "Lights out, local time.",
  title: `🏁 Next Race: ${raceName}`,
  countdown: "⏱ Countdown:",
  countdownValue: "2h 14m",
  raceLine: `🗓 Race: ${localTime}`,
};

export const remind = {
  label: "REMINDERS",
  headline: "Set it once.",
  title: `🔔 Race — Round 18`,
  prompt: "How early do you want to be reminded?",
  timings: ["15min", "30min", "1hr", "3hr"] as const,
  selected: "30min",
};

export const pushBody = `🔔 ${raceName} — Race starts in 30 minutes!`;

export const settings = {
  label: "YOURS",
  headline: "Timezone. Then language.",
  tzTitle: "🌍 Set your timezone",
  tzCurrent: "Current: UTC",
  tzPrompt: "Choose your region:",
  regions: ["🌏 Asia", "🌍 Europe", "🌎 Americas", "🌐 UTC / Other"] as const,
  langTitle: "🌐 Language / 語言",
  langCurrent: "Current: English",
  langPrompt: "Choose your language:",
  languages: ["English", "繁體中文"] as const,
};

export const cta = {
  label: "FREE",
  headline: "OpenSource",
  handle: "@F1_Infomation_bot",
  github: "Star it on GitHub",
  githubUrl: "github.com/cby0730/f1-bot",
};
