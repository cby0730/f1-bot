import { interpolate, useCurrentFrame } from "remotion";
import { startButtons } from "../copy";
import { clamp, easeOut } from "../motion";
import { colors } from "../theme";
import { BotBubble } from "../ui/TelegramChat";

export const StartPanel: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <>
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
                backgroundColor: isNext ? colors.highlight : colors.surfaceLift,
                borderRadius: 12,
                color: colors.text,
                fontSize: 20,
                fontWeight: 600,
                opacity: interpolate(frame, [12 + index * 2, 20 + index * 2], [0, 1], clamp),
                padding: "14px 10px",
                scale: isNext
                  ? interpolate(frame, [20, 36, 70], [1, 1.06, 1.06], {
                      ...clamp,
                      easing: easeOut,
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
    </>
  );
};
