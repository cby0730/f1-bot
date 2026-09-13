import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { hook } from "../copy";
import { inter } from "../fonts";
import { colors } from "../theme";

export const Hook: React.FC = () => {
  const frame = useCurrentFrame();

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
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          textAlign: "center",
          translate: interpolate(frame, [0, 8], ["0px 24px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
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
          }}
        >
          {hook.sub}
        </div>
      </div>
    </AbsoluteFill>
  );
};
