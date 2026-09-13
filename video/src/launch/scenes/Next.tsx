import { next } from "../copy";
import { colors } from "../theme";
import { BotBubble, TelegramChat } from "../ui/TelegramChat";
import { SceneChrome } from "../ui/SceneChrome";

export const Next: React.FC = () => {
  return (
    <SceneChrome label={next.label} headline={next.headline}>
      <TelegramChat>
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
      </TelegramChat>
    </SceneChrome>
  );
};
