/** 1920×1080 lockup: titles left, cropped phone bottom-right.
 *  Outer phone follows iPhone 16 Pro (~2.06:1), not a squat rounded rect. */

export const FRAME_W = 1920;
export const FRAME_H = 1080;

export const TITLE_LEFT = 108;
export const TITLE_WIDTH = 900;

export const PHONE_W = 776;
export const PHONE_H = 1602;
export const PHONE_LEFT = FRAME_W - PHONE_W - 108;
export const PHONE_TOP = 32;
/** ~15.5% of width — iPhone continuous corners, not a boxy 8% radius. */
export const PHONE_RADIUS = 120;
export const BEZEL = 12;
export const ISLAND_W = 192;
export const ISLAND_H = 38;
/** Inset from the housing top — real iPhones do not glue the island to the rim. */
export const ISLAND_TOP = 32;
/** Gap from the island’s bottom edge to the chat header. */
export const ISLAND_CLEARANCE = 44;
export const SCREEN_PAD_TOP =
  ISLAND_TOP - BEZEL + ISLAND_H + ISLAND_CLEARANCE;
export const THREAD_H = 920;
/** Park / travel past the visible thread so the outgoing card cannot peek. */
export const PARK_Y = THREAD_H + 48;
