import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { settings } from "../copy";
import { clamp, flickEase, flickY, progress } from "../motion";
import { PickerPanel } from "../panels/PickerPanel";
import { HOLD, RISE, SETTINGS_FLICK, SETTINGS_FLICK_AT } from "../timings";
import { Stage } from "../ui/Stage";
import { TelegramThread, THREAD_BODY_HEIGHT, ThreadPanel } from "../ui/TelegramChat";

export const Settings: React.FC = () => {
  const frame = useCurrentFrame();
  const flick = progress(frame, SETTINGS_FLICK_AT, SETTINGS_FLICK, flickEase);
  const langPark = THREAD_BODY_HEIGHT + 40;

  const tzY = frame < SETTINGS_FLICK_AT ? 0 : flickY(flick, "out");
  const langY =
    frame < SETTINGS_FLICK_AT
      ? langPark
      : interpolate(flick, [0, 1], [langPark, 0], { ...clamp, easing: flickEase });

  return (
    <AbsoluteFill
      style={{
        opacity: interpolate(frame, [HOLD.settings, HOLD.settings + RISE], [1, 0], clamp),
      }}
    >
      <Stage label={settings.label} headline={settings.headline}>
        <TelegramThread>
          <ThreadPanel y={tzY}>
            <PickerPanel
              title={settings.tzTitle}
              current={settings.tzCurrent}
              prompt={settings.tzPrompt}
              options={settings.regions}
              selected="🌏 Asia"
            />
          </ThreadPanel>
          <ThreadPanel y={langY}>
            <PickerPanel
              title={settings.langTitle}
              current={settings.langCurrent}
              prompt={settings.langPrompt}
              options={settings.languages}
              selected="English"
            />
          </ThreadPanel>
        </TelegramThread>
      </Stage>
    </AbsoluteFill>
  );
};
