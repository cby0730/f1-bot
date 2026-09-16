import { next } from "../copy";
import { colors } from "../theme";
import { BotBubble } from "../ui/TelegramChat";

export const NextPanel: React.FC = () => {
  return (
    <BotBubble>
      <div style={{ fontWeight: 700, marginBottom: 10 }}>{next.title}</div>
      <div style={{ color: "#d5e4f0" }}>
        📍 Marina Bay Street Circuit, Singapore
      </div>
      <div style={{ marginTop: 14 }}>{next.raceLine}</div>
      <div
        style={{
          color: colors.telegram,
          fontSize: 28,
          fontWeight: 800,
          marginTop: 16,
        }}
      >
        {next.countdown} {next.countdownValue}
      </div>
    </BotBubble>
  );
};
