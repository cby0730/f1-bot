import { interpolate, useCurrentFrame } from "remotion";
import { remind } from "../copy";
import { clamp, easeOut } from "../motion";
import { HOLD } from "../timings";
import { colors } from "../theme";
import { BotBubble } from "../ui/TelegramChat";

export const RemindPanel: React.FC = () => {
  const frame = useCurrentFrame();
  const launch = interpolate(frame, [HOLD.remind, HOLD.remind + 6], [1, 0.88], {
    ...clamp,
    easing: easeOut,
    output: "perceptual-scale",
  });

  return (
    <>
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
                      ...clamp,
                      easing: easeOut,
                      output: "perceptual-scale",
                    }) * launch
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
