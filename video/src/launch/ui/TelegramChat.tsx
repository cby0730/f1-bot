import { inter } from "../fonts";
import { colors } from "../theme";

export const TelegramChat: React.FC<{
  readonly children: React.ReactNode;
  readonly width?: number;
}> = ({ children, width = 560 }) => {
  return (
    <div
      style={{
        backgroundColor: colors.surface,
        borderRadius: 36,
        boxShadow: "0 28px 80px rgba(0, 0, 0, 0.5)",
        fontFamily: inter,
        overflow: "hidden",
        width,
      }}
    >
      <div
        style={{
          alignItems: "center",
          backgroundColor: colors.surfaceLift,
          display: "flex",
          gap: 14,
          padding: "18px 22px",
        }}
      >
        <div
          style={{
            backgroundColor: colors.telegram,
            borderRadius: 999,
            color: colors.text,
            fontSize: 18,
            fontWeight: 800,
            height: 40,
            lineHeight: "40px",
            textAlign: "center",
            width: 40,
          }}
        >
          F1
        </div>
        <div>
          <div
            style={{
              color: colors.text,
              fontSize: 22,
              fontWeight: 700,
            }}
          >
            F1 Bot
          </div>
          <div style={{ color: colors.muted, fontSize: 16 }}>
            @F1_Infomation_bot
          </div>
        </div>
      </div>
      <div style={{ padding: "22px 22px 26px" }}>{children}</div>
    </div>
  );
};

export const BotBubble: React.FC<{
  readonly children: React.ReactNode;
}> = ({ children }) => {
  return (
    <div
      style={{
        backgroundColor: colors.bubble,
        borderRadius: "18px 18px 18px 6px",
        color: colors.text,
        fontFamily: inter,
        fontSize: 22,
        lineHeight: 1.4,
        padding: "16px 18px",
        whiteSpace: "pre-wrap",
      }}
    >
      {children}
    </div>
  );
};
