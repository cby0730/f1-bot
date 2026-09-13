import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { settings } from "../copy";
import { clamp, flickEase, flickY, progress } from "../motion";
import { PickerPanel } from "../panels/PickerPanel";
import { HOLD, PLANE, RISE, SETTINGS_FLICK } from "../timings";
import { Stage } from "../ui/Stage";
import { TelegramThread, ThreadPanel } from "../ui/TelegramChat";

export const Settings: React.FC = () => {
  const frame = useCurrentFrame();
  const open = progress(frame, 0, RISE);
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
        bgOpacity={open}
        label={settings.label}
        headline={settings.headline}
        labelOpacity={interpolate(open, [0, 1], [0, 1])}
      >
        <div
          style={{
            opacity: open,
            transform: `scale(${interpolate(open, [0, 1], [0.66, 1])})`,
            transformOrigin: "50% 50%",
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
