import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { clamp } from "../launch/motion";
import { CTA } from "../launch/scenes/CTA";
import { colors } from "../launch/theme";
import { PlaneFlight } from "../launch/ui/PlaneFlight";
import { Phone } from "./Phone";
import { PhoneScreen } from "./PhoneScreen";
import { TitleColumn } from "./TitleColumn";
import { AT_CTA, HOLD, PLANE } from "./timings";

export const Pocket: React.FC = () => {
  const frame = useCurrentFrame();
  const shell = interpolate(frame, [AT_CTA, AT_CTA + 18], [1, 0], clamp);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        overflow: "hidden",
      }}
    >
      <AbsoluteFill style={{ opacity: shell }}>
        <TitleColumn />
        <Phone>
          <PhoneScreen />
        </Phone>
      </AbsoluteFill>
      <Sequence durationInFrames={HOLD.cta} from={AT_CTA} name="CTA">
        <CTA />
      </Sequence>
      <Sequence durationInFrames={PLANE} from={AT_CTA} name="Plane">
        <PlaneFlight durationInFrames={PLANE} />
      </Sequence>
    </AbsoluteFill>
  );
};
