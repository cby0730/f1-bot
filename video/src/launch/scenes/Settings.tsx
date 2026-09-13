import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { settings } from "../copy";
import { clamp, flickY, progress } from "../motion";
import { PickerPanel } from "../panels/PickerPanel";
import { FALL, RISE, SETTINGS_FLICK } from "../timings";
import { Stage } from "../ui/Stage";
import { TelegramThread, ThreadPanel } from "../ui/TelegramChat";

export const Settings: React.FC = () => {
  const frame = useCurrentFrame();
  const rise = progress(frame, 0, RISE);
  const flick = progress(frame, 45, SETTINGS_FLICK);
  const fall = progress(frame, 90, FALL);

  const tzY = frame < 45 ? 0 : flickY(flick, "out");
  const langY = frame < 45 ? flickY(0, "in") : flickY(flick, "in");

  return (
    <AbsoluteFill
      style={{
        opacity: interpolate(frame, [90, 90 + FALL], [1, 0], clamp),
        transform: `translateY(${interpolate(fall, [0, 1], [0, 160])}px)`,
      }}
    >
      <Stage
        label={settings.label}
        headline={settings.headline}
        labelOpacity={interpolate(rise, [0, 1], [0.35, 1])}
      >
        <div
          style={{
            opacity: rise,
            transform: `translateY(${interpolate(rise, [0, 1], [200, 0])}px)`,
          }}
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
        </div>
      </Stage>
    </AbsoluteFill>
  );
};
