import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { inter } from "../fonts";
import { colors } from "../theme";

export const SceneChrome: React.FC<{
  readonly label: string;
  readonly headline: string;
  readonly children?: React.ReactNode;
}> = ({ label, headline, children }) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        fontFamily: inter,
        padding: "64px 100px 56px",
      }}
    >
      <div
        style={{
          opacity: interpolate(frame, [0, 6], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
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
            lineHeight: 1.2,
            marginTop: 12,
            paddingBottom: 6,
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
          opacity: interpolate(frame, [4, 10], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          translate: interpolate(frame, [4, 10], ["0px 28px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        {children}
      </div>
    </AbsoluteFill>
  );
};
