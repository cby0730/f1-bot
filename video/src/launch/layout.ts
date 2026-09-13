/** Layout for the Settings → CTA plane. 1920×1080. */

export const FRAME_W = 1920;
export const FRAME_H = 1080;
export const CHAT_W = 760;
export const CHAT_LEFT = (FRAME_W - CHAT_W) / 2;
export const PHONE_W = 500;
export const PHONE_H = 980;

/** F1 avatar on the Settings chat header, nudged up so takeoff reads. */
export const PLANE_FROM = {
  x: CHAT_LEFT + 50,
  y: 288,
};

/** Telegram tile left of the CTA handle. */
export const PLANE_TO = {
  x: 660,
  y: 618,
};

export const PLANE_ARC = {
  x: 1320,
  y: 110,
};
