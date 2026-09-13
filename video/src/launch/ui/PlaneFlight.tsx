import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PLANE_ARC, PLANE_FROM, PLANE_TO } from "../layout";
import { clamp, easeOut } from "../motion";
import { PLANE } from "../timings";
import { TelegramIcon } from "./TelegramIcon";

const bezier = (t: number, a: number, b: number, c: number) =>
  (1 - t) * (1 - t) * a + 2 * (1 - t) * t * b + t * t * c;

export const PlaneFlight: React.FC = () => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [0, PLANE], [0, 1], { ...clamp, easing: easeOut });
  const x = bezier(t, PLANE_FROM.x, PLANE_ARC.x, PLANE_TO.x);
  const y = bezier(t, PLANE_FROM.y, PLANE_ARC.y, PLANE_TO.y);
  const size = interpolate(t, [0, 1], [52, 32]);
  const rotate = interpolate(t, [0, 1], [-28, 8]);

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
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
