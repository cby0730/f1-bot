import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { cta } from "../copy";
import { inter } from "../fonts";
import { colors } from "../theme";

export const CTA: React.FC = () => {
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
          opacity: interpolate(frame, [0, 12], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          textAlign: "center",
        }}
      >
        <div
          style={{
            color: colors.telegram,
            fontSize: 26,
            fontWeight: 700,
            letterSpacing: 5,
            marginBottom: 18,
          }}
        >
          {cta.label}
        </div>
        <div
          style={{
            color: colors.text,
            fontSize: 104,
            fontWeight: 800,
            letterSpacing: -2.4,
          }}
        >
          {cta.headline}
        </div>
        <div
          style={{
            backgroundColor: colors.telegram,
            borderRadius: 22,
            color: colors.text,
            display: "inline-block",
            fontSize: 42,
            fontWeight: 800,
            marginTop: 36,
            padding: "18px 40px",
          }}
        >
          {cta.handle}
        </div>
        <div
          style={{
            color: colors.muted,
            fontSize: 26,
            fontWeight: 500,
            marginTop: 28,
          }}
        >
          {cta.github}
        </div>
        <div
          style={{
            color: colors.label,
            fontSize: 22,
            marginTop: 8,
          }}
        >
          {cta.githubUrl}
        </div>
      </div>
    </AbsoluteFill>
  );
};
