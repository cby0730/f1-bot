import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PLANE_ARC, PLANE_FROM, PLANE_TO } from "../layout";
import { clamp, easeOut } from "../motion";
import { PLANE } from "../timings";
import { TelegramIcon } from "./TelegramIcon";

const bezier = (t: number, a: number, b: number, c: number) =>
  (1 - t) * (1 - t) * a + 2 * (1 - t) * t * b + t * t * c;

export const PlaneFlight: React.FC<{
  readonly from?: { x: number; y: number };
  readonly to?: { x: number; y: number };
  readonly arc?: { x: number; y: number };
  readonly durationInFrames?: number;
}> = ({
  from = PLANE_FROM,
  to = PLANE_TO,
  arc = PLANE_ARC,
  durationInFrames = PLANE,
}) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [0, durationInFrames], [0, 1], {
    ...clamp,
    easing: easeOut,
  });
  const x = bezier(t, from.x, arc.x, to.x);
  const y = bezier(t, from.y, arc.y, to.y);
  const size = interpolate(t, [0, 0.4, 1], [56, 104, 44]);
  const rotate = interpolate(t, [0, 1], [-22, 10]);

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 8 }}>
      <div
        style={{
          filter: "drop-shadow(0 16px 28px rgba(42, 171, 238, 0.55))",
          left: x - size / 2,
          position: "absolute",
          top: y - size / 2,
          transform: `rotate(${rotate}deg)`,
        }}
      >
        <TelegramIcon size={size} />
      </div>
    </AbsoluteFill>
  );
};
