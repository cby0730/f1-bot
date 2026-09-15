import { Composition, Folder } from "remotion";
import "./index.css";
import { Full } from "./launch/Full";
import { Short } from "./launch/Short";
import {
  FULL_DURATION,
  HOLD,
  SETTINGS_DURATION,
  SHORT_DURATION,
} from "./launch/timings";
import { CTA } from "./launch/scenes/CTA";
import { Hook } from "./launch/scenes/Hook";
import { Next } from "./launch/scenes/Next";
import { Notification } from "./launch/scenes/Notification";
import { Remind } from "./launch/scenes/Remind";
import { Settings } from "./launch/scenes/Settings";
import { Start } from "./launch/scenes/Start";
import { Pocket } from "./pocket/Pocket";
import { POCKET_DURATION } from "./pocket/timings";
import { Proof } from "./Proof";

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
      <Composition
        id="Short"
        component={Short}
        durationInFrames={SHORT_DURATION}
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
      <Composition
        id="Pocket"
        component={Pocket}
        durationInFrames={POCKET_DURATION}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Proof"
        component={Proof}
        durationInFrames={90}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
