import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { CTA_ICON_CX, CTA_ICON_CY, FRAME_H, FRAME_W } from "../layout";
import { clamp } from "../motion";
import { PLANE, PLANE_ARRIVE } from "../timings";
import { PaperPlane } from "./PaperPlane";

const START_W = 1500;
const TURN_W = 720;
const END_W = 42;
const START = { x: FRAME_W / 2, y: FRAME_H + 420 };
const TOP = { x: FRAME_W / 2, y: 120 };
const LAND = { x: CTA_ICON_CX, y: CTA_ICON_CY - 6 };

/** Continue up, then pull left across the top. */
const L1P1 = { x: FRAME_W / 2, y: -80 };
const L1P2 = { x: 90, y: 40 };
const L1P3 = { x: 150, y: 340 };
/** Down the left side, then into the tile. */
const L2P1 = { x: 60, y: 760 };
const L2P2 = { x: 400, y: 800 };

type Pt = { readonly x: number; readonly y: number };

const cubic = (t: number, a: number, b: number, c: number, d: number) => {
  const u = 1 - t;
  return u * u * u * a + 3 * u * u * t * b + 3 * u * t * t * c + t * t * t * d;
};

const cubicPt = (t: number, a: Pt, b: Pt, c: Pt, d: Pt): Pt => ({
  x: cubic(t, a.x, b.x, c.x, d.x),
  y: cubic(t, a.y, b.y, c.y, d.y),
});

const cubicTan = (t: number, a: Pt, b: Pt, c: Pt, d: Pt): Pt => {
  const u = 1 - t;
  return {
    x: 3 * u * u * (b.x - a.x) + 6 * u * t * (c.x - b.x) + 3 * t * t * (d.x - c.x),
    y: 3 * u * u * (b.y - a.y) + 6 * u * t * (c.y - b.y) + 3 * t * t * (d.y - c.y),
  };
};

const heading = (dx: number, dy: number) => (Math.atan2(dx, -dy) * 180) / Math.PI;

const unwrap = (angle: number, prev: number) => {
  let next = angle;
  while (next - prev > 180) next -= 360;
  while (next - prev < -180) next += 360;
  return next;
};

const smoothstep = (t: number) => t * t * (3 - 2 * t);

/**
 * Path tangents snap ~28° on the first bank and twitch at the cubic join.
 * Spring the nose toward a short look-ahead chord so the turn eases.
 */
const HEADING_LOOKAHEAD = 4;
const HEADING_WN = 0.32;
const HEADING_ZETA = 1;
const HEADING_CATCH = 8;

const poseAt = (frame: number, arrive: number, straightEnd: number) => {
  if (frame <= straightEnd) {
    const y = interpolate(frame, [0, straightEnd], [START.y, TOP.y], clamp);
    return { x: START.x, y, dx: 0, dy: -1 };
  }
  const u = interpolate(frame, [straightEnd, arrive], [0, 1], clamp);
  const split = 0.46;
  if (u <= split) {
    const s = u / split;
    const pt = cubicPt(s, TOP, L1P1, L1P2, L1P3);
    const tan = cubicTan(s, TOP, L1P1, L1P2, L1P3);
    return { x: pt.x, y: pt.y, dx: tan.x, dy: tan.y };
  }
  const s = (u - split) / (1 - split);
  const pt = cubicPt(s, L1P3, L2P1, L2P2, LAND);
  const tan = cubicTan(s, L1P3, L2P1, L2P2, LAND);
  return { x: pt.x, y: pt.y, dx: tan.x, dy: tan.y };
};

const headingAt = (frame: number, arrive: number, straightEnd: number) => {
  const end = Math.min(Math.max(frame, 0), arrive);
  let angle = 0;
  let velocity = 0;
  for (let f = 0; f <= end; f++) {
    const pose = poseAt(f, arrive, straightEnd);
    const ahead = poseAt(Math.min(f + HEADING_LOOKAHEAD, arrive), arrive, straightEnd);
    const chordX = ahead.x - pose.x;
    const chordY = ahead.y - pose.y;
    const useChord = Math.hypot(chordX, chordY) >= 1;
    const tangent = unwrap(
      heading(useChord ? chordX : pose.dx, useChord ? chordY : pose.dy),
      angle,
    );
    const raw = unwrap(heading(pose.dx, pose.dy), angle);
    const catchStart = arrive - HEADING_CATCH;
    const catchT = f > catchStart ? smoothstep((f - catchStart) / HEADING_CATCH) : 0;
    const target = tangent + catchT * (raw - tangent);
    velocity +=
      -2 * HEADING_ZETA * HEADING_WN * velocity -
      HEADING_WN * HEADING_WN * (angle - target);
    angle += velocity;
    if (catchT > 0) {
      angle += catchT * (raw - angle);
      velocity *= 1 - catchT;
    }
  }
  return angle;
};

export const PlaneFlight: React.FC<{
  readonly durationInFrames?: number;
}> = ({ durationInFrames = PLANE }) => {
  const frame = useCurrentFrame();
  const arrive = Math.min(PLANE_ARRIVE, durationInFrames);
  const straightEnd = Math.round(arrive * 0.39);
  const pose = poseAt(frame, arrive, straightEnd);
  const rotate = headingAt(frame, arrive, straightEnd);
  const width = interpolate(frame, [0, straightEnd, arrive], [START_W, TURN_W, END_W], clamp);
  const fade = interpolate(frame, [arrive, durationInFrames], [1, 0], clamp);
  const shadow = interpolate(frame, [0, arrive], [1, 0.08], clamp);

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 8 }}>
      <div
        style={{
          filter: `drop-shadow(0 ${24 * shadow}px ${36 * shadow}px rgba(0, 0, 0, ${0.4 * shadow}))`,
          left: pose.x,
          opacity: fade,
          position: "absolute",
          top: pose.y,
          transform: `translate(-50%, -50%) rotate(${rotate}deg)`,
          transformOrigin: "center center",
        }}
      >
        <PaperPlane width={width} />
      </div>
    </AbsoluteFill>
  );
};
