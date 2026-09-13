import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { FRAME_H, FRAME_W, PLANE_FROM } from "../layout";
import { clamp } from "../motion";
import { PLANE } from "../timings";
import { PaperPlane } from "./PaperPlane";

export const PlaneFlight: React.FC<{
  readonly durationInFrames?: number;
}> = ({ durationInFrames = PLANE }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [0, durationInFrames], [0, 1], clamp);

  const x = interpolate(t, [0, 0.28, 1], [PLANE_FROM.x, FRAME_W / 2, FRAME_W / 2]);
  const y = interpolate(
    t,
    [0, 0.28, 0.62, 1],
    [PLANE_FROM.y, FRAME_H * 0.42, FRAME_H * 0.5, FRAME_H * 0.68],
  );
  const scale = interpolate(t, [0, 0.3, 0.58, 1], [0.22, 1.05, 2.6, 7.6]);
  const rotate = interpolate(t, [0, 1], [-12, 8]);
  const opacity = interpolate(frame, [0, 3, durationInFrames - 8, durationInFrames], [0, 1, 1, 0], clamp);

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 8 }}>
      <div
        style={{
          filter: "drop-shadow(0 28px 40px rgba(0, 0, 0, 0.45))",
          left: x,
          opacity,
          position: "absolute",
          top: y,
          transform: `translate(-50%, -45%) rotate(${rotate}deg) scale(${scale})`,
          transformOrigin: "50% 70%",
        }}
      >
        <PaperPlane />
      </div>
    </AbsoluteFill>
  );
};
