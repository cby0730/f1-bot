import { Composition, Folder } from "remotion";
import "./index.css";
import { Full } from "./launch/Full";
import { Short } from "./launch/Short";
import { CTA } from "./launch/scenes/CTA";
import { Hook } from "./launch/scenes/Hook";
import { Next } from "./launch/scenes/Next";
import { Notification } from "./launch/scenes/Notification";
import { Remind } from "./launch/scenes/Remind";
import { Settings } from "./launch/scenes/Settings";
import { Start } from "./launch/scenes/Start";
import { Proof } from "./Proof";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Full"
        component={Full}
        durationInFrames={675}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Short"
        component={Short}
        durationInFrames={225}
        fps={30}
        width={1920}
        height={1080}
      />
      <Folder name="Launch-Scenes">
        <Composition
          id="Hook"
          component={Hook}
          durationInFrames={60}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition
          id="Start"
          component={Start}
          durationInFrames={105}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition
          id="Next"
          component={Next}
          durationInFrames={135}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition
          id="Remind"
          component={Remind}
          durationInFrames={90}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition
          id="Notification"
          component={Notification}
          durationInFrames={120}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition
          id="Settings"
          component={Settings}
          durationInFrames={90}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition
          id="CTA"
          component={CTA}
          durationInFrames={75}
          fps={30}
          width={1920}
          height={1080}
        />
      </Folder>
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
