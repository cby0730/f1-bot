import { linearTiming, springTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { AbsoluteFill } from "remotion";
import { CTA } from "./scenes/CTA";
import { Hook } from "./scenes/Hook";
import { Next } from "./scenes/Next";
import { Notification } from "./scenes/Notification";
import { Remind } from "./scenes/Remind";
import { Settings } from "./scenes/Settings";
import { Start } from "./scenes/Start";
import { colors } from "./theme";
import { FADE, FULL_SEQ, SLIDE_NEXT, SLIDE_NOTIFY } from "./timings";

export const Full: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={FULL_SEQ.hook} name="Hook">
          <Hook />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade({ shouldFadeOutExitingScene: true })}
          timing={linearTiming({ durationInFrames: FADE })}
        />
        <TransitionSeries.Sequence durationInFrames={FULL_SEQ.start} name="Start">
          <Start />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={slide({ direction: "from-right" })}
          timing={linearTiming({ durationInFrames: SLIDE_NEXT })}
        />
        <TransitionSeries.Sequence durationInFrames={FULL_SEQ.next} name="Next">
          <Next />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade({ shouldFadeOutExitingScene: true })}
          timing={linearTiming({ durationInFrames: FADE })}
        />
        <TransitionSeries.Sequence durationInFrames={FULL_SEQ.remind} name="Remind">
          <Remind />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={slide({ direction: "from-top" })}
          timing={springTiming({
            config: { damping: 200 },
            durationInFrames: SLIDE_NOTIFY,
            durationRestThreshold: 0.001,
          })}
        />
        <TransitionSeries.Sequence
          durationInFrames={FULL_SEQ.notification}
          name="Notification"
        >
          <Notification />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade({ shouldFadeOutExitingScene: true })}
          timing={linearTiming({ durationInFrames: FADE })}
        />
        <TransitionSeries.Sequence
          durationInFrames={FULL_SEQ.settings}
          name="Settings"
        >
          <Settings />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade({ shouldFadeOutExitingScene: true })}
          timing={linearTiming({ durationInFrames: FADE })}
        />
        <TransitionSeries.Sequence durationInFrames={FULL_SEQ.cta} name="CTA">
          <CTA />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
