import { Composition } from "remotion";
import "./index.css";
import { Proof } from "./Proof";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Proof"
      component={Proof}
      durationInFrames={90}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
