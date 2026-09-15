import { interpolate, Sequence, useCurrentFrame } from "remotion";
import { clamp, flickEase, progress } from "../launch/motion";
import { NextPanel } from "../launch/panels/NextPanel";
import { PickerPanel } from "../launch/panels/PickerPanel";
import { RemindPanel } from "../launch/panels/RemindPanel";
import { StartPanel } from "../launch/panels/StartPanel";
import { settings } from "../launch/copy";
import { inter } from "../launch/fonts";
import { colors } from "../launch/theme";
import { ChatHeader, ThreadPanel } from "../launch/ui/TelegramChat";
import { PARK_Y, SCREEN_PAD_TOP, THREAD_H } from "./layout";
import {
  AT,
  AT_LOCK_BANNER,
  AT_SETTINGS,
  AT_UNLOCK,
  AT_UNLOCK_SLIDE,
  BANNER_IN,
  FLICK,
  FLICK1,
  FLICK2,
  HOLD,
  LOCK_SLIDE,
  RISE,
  SETTINGS_FLICK,
  TZ_HOLD,
  UNLOCK_PRESS,
} from "./timings";
import { LockScreen } from "./LockScreen";

const flickY = (amount: number, role: "out" | "in", direction: "up" | "down") => {
  if (direction === "down") {
    return role === "out" ? amount * PARK_Y : (1 - amount) * -PARK_Y;
  }
  return role === "out" ? amount * -PARK_Y : (1 - amount) * PARK_Y;
};

export const PhoneScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const rise = progress(frame, AT.start - RISE, RISE);
  const f1 = progress(frame, FLICK1, FLICK, flickEase);
  const f2 = progress(frame, FLICK2, FLICK, flickEase);
  const langFlick = progress(frame, AT_SETTINGS + TZ_HOLD, SETTINGS_FLICK, flickEase);

  const startY = frame < FLICK1 ? 0 : flickY(f1, "out", "down");
  const nextY =
    frame < FLICK1
      ? flickY(0, "in", "down")
      : frame < FLICK2
        ? flickY(f1, "in", "down")
        : flickY(f2, "out", "up");
  const remindY = frame < FLICK2 ? flickY(0, "in", "up") : flickY(f2, "in", "up");

  const settingsOn = frame >= AT.lock + LOCK_SLIDE;
  const tzY = frame < AT_SETTINGS + TZ_HOLD ? 0 : flickY(langFlick, "out", "up");
  const langY =
    frame < AT_SETTINGS + TZ_HOLD
      ? PARK_Y
      : interpolate(langFlick, [0, 1], [PARK_Y, 0], {
          ...clamp,
          easing: flickEase,
        });

  const lockIn = interpolate(frame, [AT.lock, AT.lock + LOCK_SLIDE], [0, 1], {
    ...clamp,
    easing: flickEase,
  });
  const lockOut = interpolate(
    frame,
    [AT_UNLOCK_SLIDE, AT_SETTINGS],
    [0, 1],
    { ...clamp, easing: flickEase },
  );
  const lockT = frame < AT_UNLOCK_SLIDE ? lockIn : interpolate(lockOut, [0, 1], [1, 0]);
  const bannerT =
    frame < AT_UNLOCK
      ? progress(frame, AT_LOCK_BANNER, BANNER_IN)
      : interpolate(lockT, [0.2, 1], [0, 1], clamp);
  const press = progress(frame, AT_UNLOCK, UNLOCK_PRESS);
  const bannerPress = interpolate(press, [0, 0.45, 1], [1, 0.82, 0.95]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        fontFamily: inter,
        height: "100%",
        opacity: interpolate(rise, [0, 1], [0.38, 1]),
      }}
    >
      <div
        style={{
          backgroundColor: colors.surfaceLift,
          flexShrink: 0,
          paddingTop: SCREEN_PAD_TOP,
        }}
      >
        <ChatHeader />
      </div>
      <div
        style={{
          flex: 1,
          height: THREAD_H,
          overflow: "hidden",
          position: "relative",
        }}
      >
        <div style={{ opacity: settingsOn ? 0 : 1 }}>
          <Sequence
            durationInFrames={HOLD.start}
            from={AT.start}
            layout="none"
            name="Start"
          >
            <ThreadPanel y={startY}>
              <StartPanel />
            </ThreadPanel>
          </Sequence>
          <Sequence
            durationInFrames={HOLD.next + FLICK}
            from={FLICK1}
            layout="none"
            name="Next"
          >
            <ThreadPanel y={nextY}>
              <NextPanel />
            </ThreadPanel>
          </Sequence>
          <Sequence
            durationInFrames={HOLD.remind + FLICK + LOCK_SLIDE}
            from={FLICK2}
            layout="none"
            name="Remind"
          >
            <ThreadPanel y={remindY}>
              <RemindPanel />
            </ThreadPanel>
          </Sequence>
        </div>
        <div style={{ opacity: settingsOn ? 1 : 0 }}>
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
        </div>
      </div>
      <LockScreen bannerPress={bannerPress} bannerT={bannerT} lockT={lockT} />
    </div>
  );
};
