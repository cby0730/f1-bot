import {
  AbsoluteFill,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

/**
 * Toolchain proof only — not the launch film.
 * Confirms Remotion can render in this isolated `video/` project.
 */
export const Proof: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0a0a0f",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          opacity: interpolate(
            frame,
            [0, 18, durationInFrames - 12, durationInFrames],
            [0, 1, 1, 0],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            },
          ),
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 28,
        }}
      >
        <div
          style={{
            backgroundColor: "#1e2a33",
            borderRadius: 28,
            padding: "28px 32px 36px",
            width: 560,
            boxShadow: "0 24px 80px rgba(0, 0, 0, 0.45)",
          }}
        >
          <div
            style={{
              color: "#8aa0b3",
              fontFamily: "Helvetica Neue, Helvetica, Arial, sans-serif",
              fontSize: 22,
              letterSpacing: 0.4,
              marginBottom: 16,
            }}
          >
            @F1_Infomation_bot
          </div>
          <div
            style={{
              alignSelf: "flex-start",
              backgroundColor: "#2b5278",
              borderRadius: "18px 18px 18px 6px",
              color: "#ffffff",
              fontFamily: "Helvetica Neue, Helvetica, Arial, sans-serif",
              fontSize: 28,
              lineHeight: 1.35,
              maxWidth: 420,
              padding: "14px 18px",
            }}
          >
            Your pocket pit wall
          </div>
        </div>
        <div
          style={{
            color: "#c5c8d4",
            fontFamily: "Helvetica Neue, Helvetica, Arial, sans-serif",
            fontSize: 26,
            letterSpacing: 1.2,
            textTransform: "uppercase",
          }}
        >
          Remotion toolchain proof
        </div>
      </div>
    </AbsoluteFill>
  );
};
