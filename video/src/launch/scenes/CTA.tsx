import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { cta } from "../copy";
import { inter } from "../fonts";
import { CTA_ICON_SIZE } from "../layout";
import { clamp } from "../motion";
import { PLANE, PLANE_ARRIVE } from "../timings";
import { colors } from "../theme";
import { TelegramIcon } from "../ui/TelegramIcon";

export const CTA: React.FC<{
  readonly withPlane?: boolean;
}> = ({ withPlane = false }) => {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [10, 24], [0, 1], {
    ...clamp,
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const pad = withPlane
    ? interpolate(frame, [PLANE_ARRIVE - 8, PLANE_ARRIVE], [0, 1], {
        ...clamp,
        easing: Easing.bezier(0.16, 1, 0.3, 1),
      })
    : 1;
  const glyph = withPlane
    ? interpolate(frame, [PLANE_ARRIVE, PLANE], [0, 1], {
        ...clamp,
        easing: Easing.bezier(0.16, 1, 0.3, 1),
      })
    : 1;
  const iconScale = withPlane
    ? interpolate(frame, [PLANE_ARRIVE - 8, PLANE_ARRIVE], [0.9, 1], {
        ...clamp,
        easing: Easing.bezier(0.16, 1, 0.3, 1),
      })
    : 1;

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
              height: CTA_ICON_SIZE,
              opacity: pad,
              transform: `scale(${iconScale})`,
              width: CTA_ICON_SIZE,
            }}
          >
            <TelegramIcon glyphOpacity={glyph} size={CTA_ICON_SIZE} />
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
