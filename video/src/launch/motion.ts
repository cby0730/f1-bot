import { Easing, interpolate } from "remotion";

export const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
export const flickEase = Easing.inOut(Easing.cubic);

export const clamp = {
  extrapolateLeft: "clamp" as const,
  extrapolateRight: "clamp" as const,
};

export const progress = (
  frame: number,
  start: number,
  duration: number,
  easing = easeOut,
) =>
  interpolate(frame, [start, start + duration], [0, 1], {
    ...clamp,
    easing,
  });

export const flickTravel = 480;

export const flickY = (
  amount: number,
  role: "out" | "in",
  direction: "up" | "down" = "up",
) => {
  if (direction === "down") {
    return role === "out" ? amount * flickTravel : (1 - amount) * -flickTravel;
  }
  return role === "out" ? amount * -flickTravel : (1 - amount) * flickTravel;
};
