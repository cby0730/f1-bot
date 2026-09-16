import { remind } from "../copy";
import { RemindPanel } from "../panels/RemindPanel";
import { TelegramChat } from "../ui/TelegramChat";
import { SceneChrome } from "../ui/SceneChrome";

export const Remind: React.FC = () => {
  return (
    <SceneChrome label={remind.label} headline={remind.headline}>
      <TelegramChat>
        <RemindPanel />
      </TelegramChat>
    </SceneChrome>
  );
};
