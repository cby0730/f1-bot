import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { FRAME_H, FRAME_W } from "../layout";
import { clamp } from "../motion";
import { PLANE } from "../timings";
import { PaperPlane } from "./PaperPlane";

export const PlaneFlight: React.FC<{
  readonly durationInFrames?: number;
}> = ({ durationInFrames = PLANE }) => {
  const frame = useCurrentFrame();
  const y = interpolate(frame, [0, durationInFrames], [FRAME_H + 420, -480], clamp);

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 8 }}>
      <div
        style={{
          filter: "drop-shadow(0 24px 36px rgba(0, 0, 0, 0.4))",
          left: FRAME_W / 2,
          position: "absolute",
          top: y,
          transform: "translate(-50%, -50%) rotate(180deg)",
        }}
      >
        <PaperPlane width={1500} />
      </div>
    </AbsoluteFill>
  );
};
