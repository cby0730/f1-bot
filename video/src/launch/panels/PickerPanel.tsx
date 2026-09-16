import { colors } from "../theme";
import { BotBubble } from "../ui/TelegramChat";

export const PickerPanel: React.FC<{
  readonly title: string;
  readonly current: string;
  readonly prompt: string;
  readonly options: readonly string[];
  readonly selected: string;
}> = ({ title, current, prompt, options, selected }) => {
  return (
    <>
      <BotBubble>
        <div style={{ fontWeight: 700 }}>{title}</div>
        <div style={{ marginTop: 8 }}>{current}</div>
        <div style={{ marginTop: 10 }}>{prompt}</div>
      </BotBubble>
      <div style={{ display: "grid", gap: 10, marginTop: 16 }}>
        {options.map((label) => {
          const active = label === selected;
          return (
            <div
              key={label}
              style={{
                backgroundColor: active ? colors.highlight : colors.surfaceLift,
                borderRadius: 12,
                color: colors.text,
                fontSize: 22,
                fontWeight: 600,
                padding: "14px 16px",
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
