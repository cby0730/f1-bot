/** Hard layout for the one-time plane flight. 1920×1080, chat 760, phone 500. */

export const FRAME_W = 1920;
export const FRAME_H = 1080;
export const CHAT_W = 760;
export const CHAT_LEFT = (FRAME_W - CHAT_W) / 2;
export const PHONE_W = 500;
export const PHONE_H = 980;
export const PHONE_LEFT = (FRAME_W - PHONE_W) / 2;
export const PHONE_TOP = (FRAME_H - PHONE_H) / 2;

/** 30min chip — measured from the Remind hold still. */
export const PLANE_FROM = {
  x: 1144,
  y: 572,
};

/** Lock-screen Telegram tile. */
export const PLANE_TO = {
  x: 758,
  y: 368,
};

export const PLANE_ARC = {
  x: 980,
  y: 220,
};
