import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { CTA_ICON_CX, CTA_ICON_CY, FRAME_H, FRAME_W } from "../layout";
import { clamp } from "../motion";
import { PLANE } from "../timings";
import { PaperPlane } from "./PaperPlane";

const START_W = 1500;
const END_W = 46;
const START_X = FRAME_W / 2;
const START_Y = FRAME_H + 420;
/** Dart points up; Telegram's glyph points ~1 o'clock. */
const LAND_ROTATE = 43;

export const PlaneFlight: React.FC<{
  readonly durationInFrames?: number;
}> = ({ durationInFrames = PLANE }) => {
  const frame = useCurrentFrame();
  const x = interpolate(frame, [0, durationInFrames], [START_X, CTA_ICON_CX], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const y = interpolate(frame, [0, durationInFrames], [START_Y, CTA_ICON_CY], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const width = interpolate(frame, [0, durationInFrames], [START_W, END_W], {
    ...clamp,
    easing: Easing.in(Easing.quad),
  });
  const rotate = interpolate(
    frame,
    [durationInFrames * 0.45, durationInFrames],
    [0, LAND_ROTATE],
    clamp,
  );
  const fade = interpolate(
    frame,
    [durationInFrames - 7, durationInFrames],
    [1, 0],
    clamp,
  );
  const shadow = interpolate(frame, [0, durationInFrames], [1, 0.12], clamp);

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 8 }}>
      <div
        style={{
          filter: `drop-shadow(0 ${24 * shadow}px ${36 * shadow}px rgba(0, 0, 0, ${0.4 * shadow}))`,
          left: x,
          opacity: fade,
          position: "absolute",
          top: y,
          transform: `translate(-50%, -50%) rotate(${rotate}deg)`,
        }}
      >
        <PaperPlane width={width} />
      </div>
    </AbsoluteFill>
  );
};
