import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { clamp } from "./motion";
import { CTA } from "./scenes/CTA";
import { Hook } from "./scenes/Hook";
import { Notification } from "./scenes/Notification";
import { Settings } from "./scenes/Settings";
import { colors } from "./theme";
import {
  AT,
  FULL_SEQ,
  HOLD,
  PLANE,
  RISE,
  THREAD_DURATION,
  THREAD_FROM,
} from "./timings";
import { ThreadAct } from "./ThreadAct";
import { PlaneFlight } from "./ui/PlaneFlight";

const FadeOut: React.FC<{
  readonly after: number;
  readonly children: React.ReactNode;
}> = ({ after, children }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill
      style={{
        opacity: interpolate(frame, [after, after + RISE], [1, 0], clamp),
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

export const Full: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <Sequence durationInFrames={FULL_SEQ.hook} name="Hook">
        <FadeOut after={HOLD.hook}>
          <Hook />
        </FadeOut>
      </Sequence>
      <Sequence durationInFrames={THREAD_DURATION} from={THREAD_FROM} name="Thread">
        <ThreadAct />
      </Sequence>
      <Sequence
        durationInFrames={FULL_SEQ.notification}
        from={AT.notification}
        name="Notification"
      >
        <Notification morph fadeOutAfter={HOLD.notification} />
      </Sequence>
      <Sequence durationInFrames={FULL_SEQ.settings} from={AT.settings} name="Settings">
        <Settings />
      </Sequence>
      <Sequence durationInFrames={FULL_SEQ.cta} from={AT.cta} name="CTA">
        <CTA />
      </Sequence>
      <Sequence durationInFrames={PLANE} from={AT.cta} name="Plane">
        <PlaneFlight />
      </Sequence>
    </AbsoluteFill>
  );
};
