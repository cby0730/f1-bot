import { AbsoluteFill, Series } from "remotion";
import { CTA } from "./scenes/CTA";
import { Hook } from "./scenes/Hook";
import { Next } from "./scenes/Next";
import { colors } from "./theme";

export const Short: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <Series>
        <Series.Sequence durationInFrames={90} name="Hook">
          <Hook />
        </Series.Sequence>
        <Series.Sequence durationInFrames={240} name="Next">
          <Next />
        </Series.Sequence>
        <Series.Sequence durationInFrames={120} name="CTA">
          <CTA />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
