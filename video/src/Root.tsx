import { Composition, Folder } from "remotion";
import { Full } from "./launch/Full";
import { FULL_DURATION, HOLD, SETTINGS_DURATION } from "./launch/timings";
import { CTA } from "./launch/scenes/CTA";
import { Hook } from "./launch/scenes/Hook";
import { Next } from "./launch/scenes/Next";
import { Notification } from "./launch/scenes/Notification";
import { Remind } from "./launch/scenes/Remind";
import { Settings } from "./launch/scenes/Settings";
import { Start } from "./launch/scenes/Start";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Full"
        component={Full}
        durationInFrames={FULL_DURATION}
        fps={30}
        width={1920}
        height={1080}
      />
      <Folder name="Launch-Scenes">
        <Composition
          id="Hook"
          component={Hook}
          durationInFrames={HOLD.hook}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition
          id="Start"
          component={Start}
          durationInFrames={HOLD.start}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition
          id="Next"
          component={Next}
          durationInFrames={HOLD.next}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition
          id="Remind"
          component={Remind}
          durationInFrames={HOLD.remind}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition
          id="Notification"
          component={Notification}
          durationInFrames={HOLD.notification}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition
          id="Settings"
          component={Settings}
          durationInFrames={SETTINGS_DURATION}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition
          id="CTA"
          component={CTA}
          durationInFrames={HOLD.cta}
          fps={30}
          width={1920}
          height={1080}
        />
      </Folder>
    </>
  );
};
