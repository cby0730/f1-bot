/** Pocket cut. No wrap/unwrap — lock is a curtain on a fixed phone. */

export const RISE = 20;
export const FLICK = 16;
export const LOCK_SLIDE = 24;
export const BANNER_IN = 24;
export const UNLOCK_PRESS = 6;
export const PLANE = 24;
export const LOCK_HOLD = 33;
export const TZ_HOLD = 51;
export const LANG_HOLD = 50;
export const SETTINGS_FLICK = 10;

export const HOLD = {
  hook: 60,
  start: 75,
  next: 75,
  remind: 75,
  cta: 75,
} as const;

export const AT = {
  hook: 0,
  start: HOLD.hook,
  next: HOLD.hook + HOLD.start,
  remind: HOLD.hook + HOLD.start + HOLD.next,
  lock: HOLD.hook + HOLD.start + HOLD.next + HOLD.remind,
} as const;

export const FLICK1 = AT.next - FLICK;
export const FLICK2 = AT.remind - FLICK;

export const AT_LOCK_BANNER = AT.lock + LOCK_SLIDE;
export const AT_UNLOCK = AT_LOCK_BANNER + BANNER_IN + LOCK_HOLD;
export const AT_UNLOCK_SLIDE = AT_UNLOCK + UNLOCK_PRESS;
export const AT_SETTINGS = AT_UNLOCK_SLIDE + LOCK_SLIDE;
export const AT_LANG_FLICK = AT_SETTINGS + TZ_HOLD;
export const AT_LANG = AT_LANG_FLICK + SETTINGS_FLICK;
export const AT_CTA = AT_LANG + LANG_HOLD;

export const POCKET_DURATION = AT_CTA + HOLD.cta;
