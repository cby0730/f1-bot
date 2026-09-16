import { next } from "../copy";
import { NextPanel } from "../panels/NextPanel";
import { TelegramChat } from "../ui/TelegramChat";
import { SceneChrome } from "../ui/SceneChrome";

export const Next: React.FC = () => {
  return (
    <SceneChrome label={next.label} headline={next.headline}>
      <TelegramChat>
        <NextPanel />
      </TelegramChat>
    </SceneChrome>
  );
};
