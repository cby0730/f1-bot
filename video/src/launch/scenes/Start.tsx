import { start } from "../copy";
import { StartPanel } from "../panels/StartPanel";
import { TelegramChat } from "../ui/TelegramChat";
import { SceneChrome } from "../ui/SceneChrome";

export const Start: React.FC = () => {
  return (
    <SceneChrome label={start.label} headline={start.headline}>
      <TelegramChat>
        <StartPanel />
      </TelegramChat>
    </SceneChrome>
  );
};
