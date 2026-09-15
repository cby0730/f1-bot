import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { CTA_ICON_CX, CTA_ICON_CY, FRAME_H, FRAME_W } from "../layout";
import { clamp } from "../motion";
import { PLANE, PLANE_ARRIVE } from "../timings";
import { PaperPlane } from "./PaperPlane";

const START_W = 1500;
const MID_W = 780;
const END_W = 42;
const START_X = FRAME_W / 2;
const START_Y = FRAME_H + 420;
/** Dart mass sits low in the SVG; nudge so it rests in the tile, not on the rim. */
const LAND_Y = CTA_ICON_CY - 6;

export const PlaneFlight: React.FC<{
  readonly durationInFrames?: number;
}> = ({ durationInFrames = PLANE }) => {
  const frame = useCurrentFrame();
  const arrive = Math.min(PLANE_ARRIVE, durationInFrames);
  const x = interpolate(frame, [0, arrive], [START_X, CTA_ICON_CX], {
    ...clamp,
    easing: Easing.out(Easing.quad),
  });
  const y = interpolate(frame, [0, arrive], [START_Y, LAND_Y], {
    ...clamp,
    easing: Easing.out(Easing.quad),
  });
  const width = interpolate(frame, [0, 10, arrive], [START_W, MID_W, END_W], clamp);
  const fade = interpolate(frame, [arrive, durationInFrames], [1, 0], clamp);
  const shadow = interpolate(frame, [0, arrive], [1, 0.08], clamp);

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 8 }}>
      <div
        style={{
          filter: `drop-shadow(0 ${24 * shadow}px ${36 * shadow}px rgba(0, 0, 0, ${0.4 * shadow}))`,
          left: x,
          opacity: fade,
          position: "absolute",
          top: y,
          transform: "translate(-50%, -50%)",
        }}
      >
        <PaperPlane width={width} />
      </div>
    </AbsoluteFill>
  );
};
