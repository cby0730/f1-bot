/** Holds stay readable. Hero cuts are longer so the morph and plane can be seen. */

export const RISE = 24;
export const FLICK = 16;
export const PHONE_MORPH = 72;
export const WRAP = 24;
export const LOCK_SLIDE = 24;
export const BANNER_IN = 24;
export const PLANE = 24;
export const UNLOCK_PRESS = 6;
export const UNLOCK = UNLOCK_PRESS + LOCK_SLIDE + WRAP;
export const SETTINGS_FLICK = 10;
export const LOCK_HOLD = 33;
export const SETTINGS_TZ_HOLD = 51;
export const SETTINGS_LANG_HOLD = 50;
export const SETTINGS_FLICK_AT = WRAP + SETTINGS_TZ_HOLD;

export const HOLD = {
  hook: 60,
  start: 75,
  next: 75,
  remind: 75,
  notification: WRAP + LOCK_SLIDE + BANNER_IN + LOCK_HOLD,
  settings: SETTINGS_FLICK_AT + SETTINGS_FLICK + SETTINGS_LANG_HOLD,
  cta: 75,
} as const;

export const SHORT_HOLD = {
  hook: 45,
  next: 120,
  cta: 60,
} as const;

export const FULL_SEQ = {
  hook: HOLD.hook + RISE,
  start: HOLD.start + FLICK,
  next: HOLD.next + FLICK,
  remind: HOLD.remind + PHONE_MORPH,
  notification: HOLD.notification + UNLOCK,
  settings: HOLD.settings + PLANE,
  cta: HOLD.cta,
} as const;

export const FULL_OVERLAP = RISE + FLICK + FLICK + PHONE_MORPH + WRAP + PLANE;

export const FULL_DURATION =
  FULL_SEQ.hook +
  FULL_SEQ.start +
  FULL_SEQ.next +
  FULL_SEQ.remind +
  FULL_SEQ.notification +
  FULL_SEQ.settings +
  FULL_SEQ.cta -
  FULL_OVERLAP;

export const AT = {
  hook: 0,
  start: FULL_SEQ.hook - RISE,
  next: FULL_SEQ.hook - RISE + FULL_SEQ.start - FLICK,
  remind:
    FULL_SEQ.hook - RISE + FULL_SEQ.start - FLICK + FULL_SEQ.next - FLICK,
  notification:
    FULL_SEQ.hook -
    RISE +
    FULL_SEQ.start -
    FLICK +
    FULL_SEQ.next -
    FLICK +
    FULL_SEQ.remind -
    PHONE_MORPH,
  settings:
    FULL_SEQ.hook -
    RISE +
    FULL_SEQ.start -
    FLICK +
    FULL_SEQ.next -
    FLICK +
    FULL_SEQ.remind -
    PHONE_MORPH +
    FULL_SEQ.notification -
    WRAP,
  cta:
    FULL_SEQ.hook -
    RISE +
    FULL_SEQ.start -
    FLICK +
    FULL_SEQ.next -
    FLICK +
    FULL_SEQ.remind -
    PHONE_MORPH +
    FULL_SEQ.notification -
    WRAP +
    FULL_SEQ.settings -
    PLANE,
} as const;

export const THREAD_FROM = AT.start;
export const THREAD_DURATION = AT.notification - AT.start;

export const FADE = 8;
export const SHORT_SEQ = {
  hook: SHORT_HOLD.hook + FADE,
  next: SHORT_HOLD.next + FADE,
  cta: SHORT_HOLD.cta,
} as const;
export const SHORT_DURATION =
  SHORT_SEQ.hook + SHORT_SEQ.next + SHORT_SEQ.cta - FADE - FADE;

export const SETTINGS_DURATION = HOLD.settings;
