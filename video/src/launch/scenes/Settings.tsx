import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { settings } from "../copy";
import { clamp, flickEase, flickY, progress } from "../motion";
import { PickerPanel } from "../panels/PickerPanel";
import { HOLD, PLANE, RISE, SETTINGS_FLICK } from "../timings";
import { Stage } from "../ui/Stage";
import { TelegramThread, ThreadPanel } from "../ui/TelegramChat";

export const Settings: React.FC = () => {
  const frame = useCurrentFrame();
  const reveal = progress(frame, 6, RISE - 6);
  const flick = progress(frame, 45, SETTINGS_FLICK, flickEase);

  const tzY = frame < 45 ? 0 : flickY(flick, "out");
  const langY = frame < 45 ? flickY(0, "in") : flickY(flick, "in");

  return (
    <AbsoluteFill
      style={{
        opacity: interpolate(frame, [HOLD.settings, HOLD.settings + PLANE], [1, 0], clamp),
      }}
    >
      <Stage
        bgOpacity={reveal}
        label={settings.label}
        headline={settings.headline}
        labelOpacity={reveal}
      >
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
