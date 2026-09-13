import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { hook } from "../copy";
import { inter } from "../fonts";
import { clamp } from "../motion";
import { colors } from "../theme";
import { RISE } from "../timings";

export const Hook: React.FC<{
  readonly leaveAfter?: number;
}> = ({ leaveAfter }) => {
  const frame = useCurrentFrame();
  const leave = leaveAfter
    ? interpolate(frame, [leaveAfter, leaveAfter + RISE], [0, 1], {
        ...clamp,
        easing: Easing.bezier(0.16, 1, 0.3, 1),
      })
    : 0;

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        backgroundColor: colors.bg,
        fontFamily: inter,
        justifyContent: "center",
      }}
    >
      <div
        style={{
          opacity: interpolate(frame, [0, 8], [0, 1], {
            ...clamp,
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          textAlign: "center",
          translate: interpolate(frame, [0, 8], ["0px 24px", "0px 0px"], {
            ...clamp,
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        <div
          style={{
            color: colors.telegram,
            fontSize: 28,
            fontWeight: 700,
            letterSpacing: 5,
            marginBottom: 22,
            opacity: interpolate(leave, [0, 0.45], [1, 0], clamp),
          }}
        >
          {hook.label}
        </div>
        <div
          style={{
            color: colors.text,
            fontSize: 120,
            fontWeight: 800,
            letterSpacing: -3,
            lineHeight: 0.98,
            opacity: interpolate(leave, [0.7, 1], [1, 0], clamp),
            transform: `translate(${interpolate(leave, [0, 1], [0, -90])}px, ${interpolate(leave, [0, 1], [0, -210])}px) scale(${interpolate(leave, [0, 1], [1, 0.2])})`,
            transformOrigin: "50% 40%",
          }}
        >
          {hook.headline}
        </div>
        <div
          style={{
            color: colors.muted,
            fontSize: 36,
            fontWeight: 500,
            marginTop: 28,
            opacity: interpolate(leave, [0, 0.4], [1, 0], clamp),
          }}
        >
          {hook.sub}
        </div>
      </div>
    </AbsoluteFill>
  );
};
