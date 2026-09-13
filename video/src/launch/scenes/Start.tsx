import { Easing, interpolate, useCurrentFrame } from "remotion";
import { start, startButtons } from "../copy";
import { colors } from "../theme";
import { BotBubble, TelegramChat } from "../ui/TelegramChat";
import { SceneChrome } from "../ui/SceneChrome";

export const Start: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <SceneChrome label={start.label} headline={start.headline}>
      <TelegramChat>
        <BotBubble>
          Welcome to F1 Bot! Get Formula 1 race info, standings, and session
          results.
        </BotBubble>
        <div
          style={{
            display: "grid",
            gap: 10,
            gridTemplateColumns: "1fr 1fr",
            marginTop: 16,
          }}
        >
          {startButtons.map((label, index) => {
            const isNext = label.startsWith("🏁");
            return (
              <div
                key={label}
                style={{
                  backgroundColor: isNext
                    ? colors.highlight
                    : colors.surfaceLift,
                  borderRadius: 12,
                  color: colors.text,
                  fontSize: 20,
                  fontWeight: 600,
                  padding: "14px 10px",
                  scale: isNext
                    ? interpolate(frame, [20, 36, 70], [1, 1.06, 1.06], {
                        extrapolateLeft: "clamp",
                        extrapolateRight: "clamp",
                        easing: Easing.bezier(0.16, 1, 0.3, 1),
                        output: "perceptual-scale",
                      })
                    : 1,
                  textAlign: "center",
                  opacity: interpolate(
                    frame,
                    [12 + index * 2, 20 + index * 2],
                    [0, 1],
                    {
                      extrapolateLeft: "clamp",
                      extrapolateRight: "clamp",
                    },
                  ),
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
