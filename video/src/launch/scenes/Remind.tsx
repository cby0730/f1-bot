import { Easing, interpolate, useCurrentFrame } from "remotion";
import { remind } from "../copy";
import { colors } from "../theme";
import { BotBubble, TelegramChat } from "../ui/TelegramChat";
import { SceneChrome } from "../ui/SceneChrome";

export const Remind: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <SceneChrome label={remind.label} headline={remind.headline}>
      <TelegramChat>
        <BotBubble>
          <div style={{ fontWeight: 700 }}>{remind.title}</div>
          <div style={{ marginTop: 10 }}>{remind.prompt}</div>
        </BotBubble>
        <div
          style={{
            display: "grid",
            gap: 10,
            gridTemplateColumns: "1fr 1fr",
            marginTop: 16,
          }}
        >
          {remind.timings.map((label) => {
            const selected = label === remind.selected;
            return (
              <div
                key={label}
                style={{
                  backgroundColor: selected
                    ? colors.highlight
                    : colors.surfaceLift,
                  borderRadius: 12,
                  color: colors.text,
                  fontSize: 24,
                  fontWeight: 700,
                  padding: "16px 10px",
                  scale: selected
                    ? interpolate(frame, [16, 32], [1, 1.08], {
                        extrapolateLeft: "clamp",
                        extrapolateRight: "clamp",
                        easing: Easing.bezier(0.16, 1, 0.3, 1),
                        output: "perceptual-scale",
                      })
                    : 1,
                  textAlign: "center",
                }}
              >
                {label}
              </div>
            );
          })}
        </div>
      </TelegramChat>
    </SceneChrome>
  );
};
