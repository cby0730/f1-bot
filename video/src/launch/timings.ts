/** Readable holds. Overlaps are padded onto the outgoing beat so Full stays 22.5s. */

export const RISE = 10;
export const FLICK = 10;
export const PLANE = 12;
export const FALL = 10;
export const SETTINGS_FLICK = 6;

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
  hook: HOLD.hook + RISE,
  start: HOLD.start + FLICK,
  next: HOLD.next + FLICK,
  remind: HOLD.remind + PLANE,
  notification: HOLD.notification + RISE,
  settings: HOLD.settings + FALL,
  cta: HOLD.cta,
} as const;

export const FULL_OVERLAP = RISE + FLICK + FLICK + PLANE + RISE + FALL;

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
    PLANE,
  settings:
    FULL_SEQ.hook -
    RISE +
    FULL_SEQ.start -
    FLICK +
    FULL_SEQ.next -
    FLICK +
    FULL_SEQ.remind -
    PLANE +
    FULL_SEQ.notification -
    RISE,
  cta:
    FULL_SEQ.hook -
    RISE +
    FULL_SEQ.start -
    FLICK +
    FULL_SEQ.next -
    FLICK +
    FULL_SEQ.remind -
    PLANE +
    FULL_SEQ.notification -
    RISE +
    FULL_SEQ.settings -
    FALL,
} as const;

export const THREAD_FROM = AT.start;
export const THREAD_DURATION = AT.notification + PLANE - AT.start;

export const FADE = 8;
export const SHORT_SEQ = {
  hook: SHORT_HOLD.hook + FADE,
  next: SHORT_HOLD.next + FADE,
  cta: SHORT_HOLD.cta,
} as const;
export const SHORT_DURATION =
  SHORT_SEQ.hook + SHORT_SEQ.next + SHORT_SEQ.cta - FADE - FADE;

export const SETTINGS_DURATION = HOLD.settings;
