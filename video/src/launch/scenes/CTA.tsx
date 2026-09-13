import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { cta } from "../copy";
import { inter } from "../fonts";
import { PLANE } from "../timings";
import { colors } from "../theme";
import { TelegramIcon } from "../ui/TelegramIcon";

export const CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [10, 24], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const dock = interpolate(frame, [PLANE - 8, PLANE], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        backgroundColor: "transparent",
        fontFamily: inter,
        justifyContent: "center",
      }}
    >
      <div
        style={{
          opacity: enter,
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
            alignItems: "center",
            display: "inline-flex",
            gap: 16,
            justifyContent: "center",
            marginTop: 36,
          }}
        >
          <div
            style={{
              height: 56,
              opacity: dock,
              transform: `scale(${0.6 + 0.4 * dock})`,
              width: 56,
            }}
          >
            <TelegramIcon size={56} />
          </div>
          <div
            style={{
              backgroundColor: colors.telegram,
              borderRadius: 22,
              color: colors.text,
              fontSize: 42,
              fontWeight: 800,
              padding: "18px 40px",
            }}
          >
            {cta.handle}
          </div>
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
