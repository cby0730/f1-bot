import { inter } from "../fonts";
import { colors } from "../theme";

export const CHAT_WIDTH = 760;
export const THREAD_BODY_HEIGHT = 520;

export const ChatHeader: React.FC = () => {
  return (
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
  );
};

export const TelegramChat: React.FC<{
  readonly children: React.ReactNode;
  readonly width?: number;
}> = ({ children, width = CHAT_WIDTH }) => {
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
      <ChatHeader />
      <div style={{ padding: "22px 22px 26px" }}>{children}</div>
    </div>
  );
};

export const TelegramThread: React.FC<{
  readonly children: React.ReactNode;
  readonly width?: number;
}> = ({ children, width = CHAT_WIDTH }) => {
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
      <ChatHeader />
      <div
        style={{
          height: THREAD_BODY_HEIGHT,
          overflow: "hidden",
          position: "relative",
        }}
      >
        {children}
      </div>
    </div>
  );
};

export const ThreadPanel: React.FC<{
  readonly children: React.ReactNode;
  readonly y: number;
}> = ({ children, y }) => {
  return (
    <div
      style={{
        left: 0,
        padding: "22px 22px 26px",
        position: "absolute",
        right: 0,
        top: 0,
        transform: `translateY(${y}px)`,
      }}
    >
      {children}
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
        fontSize: 24,
        lineHeight: 1.4,
        padding: "18px 20px",
        whiteSpace: "pre-wrap",
      }}
    >
      {children}
    </div>
  );
};
