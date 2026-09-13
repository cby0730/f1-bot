import { AbsoluteFill, Series } from "remotion";
import { CTA } from "./scenes/CTA";
import { Hook } from "./scenes/Hook";
import { Next } from "./scenes/Next";
import { Notification } from "./scenes/Notification";
import { Remind } from "./scenes/Remind";
import { Settings } from "./scenes/Settings";
import { Start } from "./scenes/Start";
import { colors } from "./theme";

export const Full: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <Series>
        <Series.Sequence durationInFrames={120} name="Hook">
          <Hook />
        </Series.Sequence>
        <Series.Sequence durationInFrames={210} name="Start">
          <Start />
        </Series.Sequence>
        <Series.Sequence durationInFrames={270} name="Next">
          <Next />
        </Series.Sequence>
        <Series.Sequence durationInFrames={180} name="Remind">
          <Remind />
        </Series.Sequence>
        <Series.Sequence durationInFrames={240} name="Notification">
          <Notification />
        </Series.Sequence>
        <Series.Sequence durationInFrames={180} name="Settings">
          <Settings />
        </Series.Sequence>
        <Series.Sequence durationInFrames={150} name="CTA">
          <CTA />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
