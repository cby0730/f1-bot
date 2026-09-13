import { AbsoluteFill, Series } from "remotion";
import { CTA } from "./scenes/CTA";
import { Hook } from "./scenes/Hook";
import { Next } from "./scenes/Next";
import { colors } from "./theme";

export const Short: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <Series>
        <Series.Sequence durationInFrames={45} name="Hook">
          <Hook />
        </Series.Sequence>
        <Series.Sequence durationInFrames={120} name="Next">
          <Next />
        </Series.Sequence>
        <Series.Sequence durationInFrames={60} name="CTA">
          <CTA />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
