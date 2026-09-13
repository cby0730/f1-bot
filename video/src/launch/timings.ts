/** Readable holds. TransitionSeries overlaps, so each outgoing sequence is padded. */

export const FADE = 8;
export const SLIDE_NEXT = 8;
export const SLIDE_NOTIFY = 10;
export const SETTINGS_PICKER_FADE = 6;

export const HOLD = {
  hook: 60,
  start: 105,
  next: 135,
  remind: 90,
  notification: 120,
  settings: 90,
  cta: 75,
} as const;

export const SHORT_HOLD = {
  hook: 45,
  next: 120,
  cta: 60,
} as const;

export const FULL_SEQ = {
  hook: HOLD.hook + FADE,
  start: HOLD.start + SLIDE_NEXT,
  next: HOLD.next + FADE,
  remind: HOLD.remind + SLIDE_NOTIFY,
  notification: HOLD.notification + FADE,
  settings: HOLD.settings + FADE,
  cta: HOLD.cta,
} as const;

export const FULL_TRANSITIONS =
  FADE + SLIDE_NEXT + FADE + SLIDE_NOTIFY + FADE + FADE;

export const FULL_DURATION =
  FULL_SEQ.hook +
  FULL_SEQ.start +
  FULL_SEQ.next +
  FULL_SEQ.remind +
  FULL_SEQ.notification +
  FULL_SEQ.settings +
  FULL_SEQ.cta -
  FULL_TRANSITIONS;

export const SHORT_SEQ = {
  hook: SHORT_HOLD.hook + FADE,
  next: SHORT_HOLD.next + FADE,
  cta: SHORT_HOLD.cta,
} as const;

export const SHORT_TRANSITIONS = FADE + FADE;

export const SHORT_DURATION =
  SHORT_SEQ.hook + SHORT_SEQ.next + SHORT_SEQ.cta - SHORT_TRANSITIONS;

export const SETTINGS_TZ = 45 + SETTINGS_PICKER_FADE;
export const SETTINGS_LANG = 45 + FADE;
export const SETTINGS_DURATION =
  SETTINGS_TZ + SETTINGS_LANG - SETTINGS_PICKER_FADE;
