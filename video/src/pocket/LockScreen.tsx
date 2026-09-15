import { interpolate } from "remotion";
import { lockDate, lockPeriod, lockTime, pushBody } from "../launch/copy";
import { inter } from "../launch/fonts";
import { clamp } from "../launch/motion";
import { colors } from "../launch/theme";
import { TelegramIcon } from "../launch/ui/TelegramIcon";

export const LockScreen: React.FC<{
  readonly lockT: number;
  readonly bannerT: number;
  readonly bannerPress: number;
}> = ({ lockT, bannerT, bannerPress }) => {
  return (
    <div
      style={{
        fontFamily: inter,
        inset: 0,
        pointerEvents: "none",
        position: "absolute",
        zIndex: 4,
      }}
    >
      <div
        style={{
          background:
            "radial-gradient(circle at 50% 0%, #243044 0%, #0c0e14 55%)",
          inset: 0,
          position: "absolute",
          transform: `translateY(${interpolate(lockT, [0, 1], [-100, 0])}%)`,
        }}
      />
      <div
        style={{
          inset: 0,
          opacity: interpolate(lockT, [0.2, 0.75], [0, 1], clamp),
          padding: "88px 28px 0",
          position: "absolute",
        }}
      >
        <div
          style={{
            color: colors.text,
            fontSize: 88,
            fontWeight: 700,
            letterSpacing: -2,
            lineHeight: 0.9,
            textAlign: "center",
          }}
        >
          {lockTime}
          <span style={{ fontSize: 34, marginLeft: 8 }}>{lockPeriod}</span>
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
            marginTop: 44,
            opacity: bannerT,
            padding: "16px 16px 18px",
            transform: `translateY(${interpolate(bannerT, [0, 1], [20, 0])}px) scale(${bannerPress})`,
            transformOrigin: "50% 50%",
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
            <TelegramIcon size={32} />
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
            <div style={{ color: colors.muted, fontSize: 14 }}>
              now
            </div>
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
  );
};
