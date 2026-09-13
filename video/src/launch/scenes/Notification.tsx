import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { lockDate, lockPeriod, lockTime, pushBody } from "../copy";
import { inter } from "../fonts";
import { colors } from "../theme";
import { TelegramIcon } from "../ui/TelegramIcon";

export const Notification: React.FC<{
  readonly dockIconAt?: number;
  readonly fadeOutAfter?: number;
}> = ({ dockIconAt, fadeOutAfter }) => {
  const frame = useCurrentFrame();
  const iconOpacity = dockIconAt
    ? interpolate(frame, [dockIconAt - 2, dockIconAt], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;
  const bannerFrom = dockIconAt ? 0 : 8;
  const exit = fadeOutAfter
    ? interpolate(frame, [fadeOutAfter, fadeOutAfter + 10], [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;
  const exitY = fadeOutAfter
    ? interpolate(frame, [fadeOutAfter, fadeOutAfter + 10], [0, 70], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        backgroundColor: colors.bg,
        fontFamily: inter,
        justifyContent: "center",
        opacity: exit,
        transform: `translateY(${exitY}px)`,
      }}
    >
      <div
        style={{
          backgroundColor: "#111318",
          borderRadius: 64,
          boxShadow: "0 30px 90px rgba(0, 0, 0, 0.55)",
          height: 980,
          overflow: "hidden",
          position: "relative",
          scale: interpolate(frame, [0, 16], [0.94, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
            output: "perceptual-scale",
          }),
          width: 500,
        }}
      >
        <div
          style={{
            background:
              "radial-gradient(circle at 50% 0%, #243044 0%, #0c0e14 55%)",
            height: "100%",
            padding: "28px 24px 0",
          }}
        >
          <div
            style={{
              backgroundColor: colors.text,
              borderRadius: 999,
              height: 28,
              margin: "0 auto 36px",
              opacity: 0.92,
              width: 120,
            }}
          />
          <div
            style={{
              color: colors.text,
              fontSize: 92,
              fontWeight: 700,
              letterSpacing: -2,
              lineHeight: 0.9,
              textAlign: "center",
            }}
          >
            {lockTime}
            <span style={{ fontSize: 36, marginLeft: 8 }}>{lockPeriod}</span>
          </div>
          <div
            style={{
              color: colors.muted,
              fontSize: 22,
              fontWeight: 500,
              marginTop: 10,
              textAlign: "center",
            }}
          >
            {lockDate}
          </div>
          <div
            style={{
              backgroundColor: "rgba(36, 40, 48, 0.92)",
              borderRadius: 22,
              marginTop: 48,
              opacity: interpolate(frame, [bannerFrom, bannerFrom + 8], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.bezier(0.16, 1, 0.3, 1),
              }),
              padding: "16px 16px 18px",
              translate: interpolate(frame, [bannerFrom, bannerFrom + 8], ["0px 20px", "0px 0px"], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.bezier(0.16, 1, 0.3, 1),
              }),
            }}
          >
            <div
              style={{
                alignItems: "center",
                display: "flex",
                gap: 10,
                marginBottom: 8,
              }}
            >
              <div style={{ opacity: iconOpacity }}>
                <TelegramIcon size={32} />
              </div>
              <div
                style={{
                  color: colors.muted,
                  flex: 1,
                  fontSize: 15,
                  fontWeight: 700,
                  letterSpacing: 0.4,
                  textTransform: "uppercase",
                }}
              >
                Telegram
              </div>
              <div style={{ color: colors.muted, fontSize: 14 }}>now</div>
            </div>
            <div
              style={{
                color: colors.text,
                fontSize: 22,
                fontWeight: 600,
                lineHeight: 1.35,
              }}
            >
              {pushBody}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
