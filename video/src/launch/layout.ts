/** Hard layout for the one-time plane flight. 1920×1080, chat 760, phone 500. */

export const FRAME_W = 1920;
export const FRAME_H = 1080;
export const CHAT_W = 760;
export const CHAT_LEFT = (FRAME_W - CHAT_W) / 2;
export const PHONE_W = 500;
export const PHONE_H = 980;
export const PHONE_LEFT = (FRAME_W - PHONE_W) / 2;
export const PHONE_TOP = (FRAME_H - PHONE_H) / 2;

/** 30min chip — right column of the Remind 2×2 grid. */
export const PLANE_FROM = {
  x: CHAT_LEFT + 22 + (CHAT_W - 44) / 2 + 10 + (CHAT_W - 44) / 4,
  y: 652,
};

/** Lock-screen Telegram tile. */
export const PLANE_TO = {
  x: PHONE_LEFT + 24 + 16 + 16,
  y: PHONE_TOP + 28 + 28 + 36 + 92 + 10 + 22 + 48 + 16 + 16,
};

export const PLANE_ARC = {
  x: (PLANE_FROM.x + PLANE_TO.x) / 2 - 40,
  y: 260,
};
