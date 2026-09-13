import { interpolate, useCurrentFrame } from "remotion";
import { inter } from "../fonts";
import { clamp, easeOut } from "../motion";
import { colors } from "../theme";

export const Stage: React.FC<{
  readonly label: string;
  readonly headline: string;
  readonly children?: React.ReactNode;
  readonly labelOpacity?: number;
  readonly bgOpacity?: number;
}> = ({ label, headline, children, labelOpacity, bgOpacity = 1 }) => {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [0, 6], [0, 1], { ...clamp, easing: easeOut });

  return (
    <div
      style={{
        backgroundColor:
          bgOpacity >= 1 ? colors.bg : `rgba(7, 8, 12, ${bgOpacity})`,
        display: "flex",
        flexDirection: "column",
        fontFamily: inter,
        height: "100%",
        padding: "64px 100px 56px",
        width: "100%",
      }}
    >
      <div style={{ opacity: labelOpacity ?? enter }}>
        <div
          style={{
            color: colors.label,
            fontSize: 26,
            fontWeight: 600,
            letterSpacing: 4,
            textTransform: "uppercase",
          }}
        >
          {label}
        </div>
        <div
          style={{
            color: colors.text,
            fontSize: 64,
            fontWeight: 800,
            letterSpacing: -1.6,
            lineHeight: 1.05,
            marginTop: 12,
          }}
        >
          {headline}
        </div>
      </div>
      <div
        style={{
          alignItems: "center",
          display: "flex",
          flex: 1,
          justifyContent: "center",
          minHeight: 0,
        }}
      >
        {children}
      </div>
    </div>
  );
};
