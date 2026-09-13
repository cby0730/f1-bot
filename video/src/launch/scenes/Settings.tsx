import { interpolate, useCurrentFrame } from "remotion";
import { settings } from "../copy";
import { colors } from "../theme";
import { SETTINGS_PICKER_FADE } from "../timings";
import { BotBubble, TelegramChat } from "../ui/TelegramChat";
import { SceneChrome } from "../ui/SceneChrome";

const Picker: React.FC<{
  readonly title: string;
  readonly current: string;
  readonly prompt: string;
  readonly options: readonly string[];
  readonly selected: string;
}> = ({ title, current, prompt, options, selected }) => {
  return (
    <TelegramChat>
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
    </TelegramChat>
  );
};

export const Settings: React.FC = () => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [45, 45 + SETTINGS_PICKER_FADE], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <SceneChrome label={settings.label} headline={settings.headline}>
      <div style={{ height: 620, position: "relative", width: 760 }}>
        <div style={{ left: 0, position: "absolute", top: 0, width: "100%" }}>
          <Picker
            title={settings.tzTitle}
            current={settings.tzCurrent}
            prompt={settings.tzPrompt}
            options={settings.regions}
            selected="🌏 Asia"
          />
        </div>
        <div
          style={{
            backgroundColor: colors.bg,
            left: 0,
            minHeight: 620,
            opacity: fade,
            position: "absolute",
            top: 0,
            width: "100%",
          }}
        >
          <Picker
            title={settings.langTitle}
            current={settings.langCurrent}
            prompt={settings.langPrompt}
            options={settings.languages}
            selected="English"
          />
        </div>
      </div>
    </SceneChrome>
  );
};
