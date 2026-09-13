import { linearTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { AbsoluteFill } from "remotion";
import { settings } from "../copy";
import { colors } from "../theme";
import {
  SETTINGS_LANG,
  SETTINGS_PICKER_FADE,
  SETTINGS_TZ,
} from "../timings";
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

const PickerSlot: React.FC<{ readonly children: React.ReactNode }> = ({
  children,
}) => {
  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        display: "flex",
        justifyContent: "center",
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

export const Settings: React.FC = () => {
  return (
    <SceneChrome label={settings.label} headline={settings.headline}>
      <div
        style={{
          height: "100%",
          minHeight: 640,
          position: "relative",
          width: "100%",
        }}
      >
        <TransitionSeries>
          <TransitionSeries.Sequence durationInFrames={SETTINGS_TZ} name="Timezone">
            <PickerSlot>
              <Picker
                title={settings.tzTitle}
                current={settings.tzCurrent}
                prompt={settings.tzPrompt}
                options={settings.regions}
                selected="🌏 Asia"
              />
            </PickerSlot>
          </TransitionSeries.Sequence>
          <TransitionSeries.Transition
            presentation={fade({ shouldFadeOutExitingScene: true })}
            timing={linearTiming({ durationInFrames: SETTINGS_PICKER_FADE })}
          />
          <TransitionSeries.Sequence
            durationInFrames={SETTINGS_LANG}
            name="Language"
          >
            <PickerSlot>
              <Picker
                title={settings.langTitle}
                current={settings.langCurrent}
                prompt={settings.langPrompt}
                options={settings.languages}
                selected="English"
              />
            </PickerSlot>
          </TransitionSeries.Sequence>
        </TransitionSeries>
      </div>
    </SceneChrome>
  );
};
