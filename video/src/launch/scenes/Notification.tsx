import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { lockDate, lockPeriod, lockTime, pushBody, remind } from "../copy";
import { inter } from "../fonts";
import { CHAT_W, PHONE_H, PHONE_W } from "../layout";
import { clamp, progress } from "../motion";
import { RemindPanel } from "../panels/RemindPanel";
import { colors } from "../theme";
import { BANNER_IN, LOCK_SLIDE, RISE, WRAP } from "../timings";
import { Stage } from "../ui/Stage";
import { ChatHeader } from "../ui/TelegramChat";
import { TelegramIcon } from "../ui/TelegramIcon";

const CHAT_H = 596;

export const Notification: React.FC<{
  readonly morph?: boolean;
  readonly fadeOutAfter?: number;
}> = ({ morph = false, fadeOutAfter }) => {
  const frame = useCurrentFrame();
  const wrapT = morph ? progress(frame, 0, WRAP) : 1;
  const lockT = morph
    ? interpolate(frame, [WRAP, WRAP + LOCK_SLIDE], [0, 1], {
        ...clamp,
        easing: Easing.inOut(Easing.cubic),
      })
    : 1;
  const bannerT = morph
    ? progress(frame, WRAP + LOCK_SLIDE, BANNER_IN)
    : progress(frame, 8, 8);
  const labelFade = morph ? interpolate(wrapT, [0, 1], [1, 0]) : 0;
  const press = fadeOutAfter ? progress(frame, fadeOutAfter, 6) : 0;
  const unlock = fadeOutAfter
    ? interpolate(frame, [fadeOutAfter + 6, fadeOutAfter + RISE], [0, 1], {
        ...clamp,
        easing: Easing.bezier(0.22, 1, 0.36, 1),
      })
    : 0;
  const bannerPress = interpolate(press, [0, 0.5, 1], [1, 0.88, 0.94]);
  const phoneY = interpolate(unlock, [0, 1], [0, -1120]);

  const width = interpolate(wrapT, [0, 1], [CHAT_W, PHONE_W]);
  const height = interpolate(wrapT, [0, 1], [CHAT_H, PHONE_H]);
  const radius = interpolate(wrapT, [0, 1], [36, 64]);

  const phone = (
    <div
      style={{
        backgroundColor: "#111318",
        borderRadius: radius,
        boxShadow: "0 30px 90px rgba(0, 0, 0, 0.55)",
        fontFamily: inter,
        height,
        overflow: "hidden",
        position: "relative",
        transform: `translateY(${phoneY}px)`,
        width,
      }}
    >
      <div
        style={{
          backgroundColor: colors.surface,
          height: "100%",
        }}
      >
        <div style={{ opacity: interpolate(wrapT, [0, 0.75], [1, 0], clamp) }}>
          <ChatHeader />
        </div>
        <div
          style={{
            padding: `${interpolate(wrapT, [0, 1], [22, 120])}px 22px 26px`,
          }}
        >
          <RemindPanel pickerOpacity={interpolate(wrapT, [0, 0.7], [1, 0], clamp)} />
        </div>
      </div>

      <div
        style={{
          backgroundColor: colors.text,
          borderRadius: 999,
          height: 28,
          left: "50%",
          marginLeft: -60,
          opacity: interpolate(wrapT, [0.25, 1], [0, 0.92], clamp),
          position: "absolute",
          top: 22,
          width: 120,
          zIndex: 2,
        }}
      />

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
          padding: "28px 24px 0",
          position: "absolute",
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
  );

  if (!morph) {
    return (
      <AbsoluteFill
        style={{
          alignItems: "center",
          backgroundColor: colors.bg,
          fontFamily: inter,
          justifyContent: "center",
        }}
      >
        {phone}
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <Stage label={remind.label} headline={remind.headline} labelOpacity={labelFade}>
        {phone}
      </Stage>
    </AbsoluteFill>
  );
};
