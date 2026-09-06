# F1 Bot 的 SaaS 風格發表影片

## Goal

為現有的 F1 Telegram Bot 做兩支**看起來像 SaaS 產品發表片**的英文影片：一支短、可循環；一支完整發表。產品本身不變、也不改成付費 SaaS。目的是讓還沒用過的人立刻知道：這是給 Telegram 上 F1 球迷的產品，值得去開 bot。

## Success criteria

- 交出兩支英文影片檔：短循環版 + 完整發表版。
- 兩支都可靜音看懂；完整版可以有音樂，但沒有旁白也可以。
- 沒用不的人看完能回答：這是什麼、為什麼跟一般聊天 bot 不一樣、要去 Telegram 用。
- 片子明確說這是給 Telegram 使用者／Telegram 上的 F1 球迷，不會讓人以為這是網站或付費 SaaS。
- 主線看得到：下一場／倒數 → 成績或積分 → 冠軍鎖定；時區、語言、以及「都是 Telegram 簡易 UI」只出現一句或一個短拍。

## Non-goals and boundaries

- 不把 bot 做成 SaaS，不講訂閱或定價。
- 不做落地頁、不改 README、不取代 `demo.gif`（那是下一階段）。
- 這次不要旁白、不要 TTS、不要繁中版。
- 不列出 9 個或 16 個指令，不當教學片。
- 不宣稱 LINE、不宣稱獨家數據。
- 主畫面不是真實 Telegram 對話錄影；Telegram 只用來表明身分與行動。

## Users / context

還沒用過的人，以及 Telegram 上的 F1 球迷。短片以後可以進 README；完整片用來對外貼。這次他們都還只是「收到兩支檔」的觀眾。

## Constraints

- 產品是免費 Telegram bot（`@F1_Infomation_bot`），不是網頁產品。
- 這次畫面與文字只做英文。
- 賣點是體驗（兩段式操作、冠軍鎖定、在地時區／語言），不是資料來源。
- 真實聊天泡泡很難達到你要的 SaaS 質感，所以產品資訊用重新設計過的介面呈現。

## Unknowns map

### Known knowns

- 現有 F1 Telegram Bot，16 個指令，中英、時區、提醒都已上線。
- 要 SaaS 發表片的質感，但身分必須是 Telegram。
- 兩支英文、可靜音；這次只交檔。

### Known unknowns

- 短片與完整片各要幾秒。
- 完整版要不要配樂、什麼情緒。
- 結尾行動要偏「開 bot」還是「看 GitHub」。

### Unknown knowns

- 「專業」指的是 Linear / Raycast 那種短發表片，不是教學長片。
- 時區／語言／好上手要被提到，但不能蓋過主線。
- 旁白想要，但這次先不當成功條件。

### Unknown unknowns

- 重設計的產品畫面，會不會看起來像另一個產品（已用「必須點名 Telegram」壓住）。
- 沒有真實 Telegram 操作，會不會讓人不知道實際長什麼樣子。

### Remaining open questions

- 兩支片子的大概長度。
- 下一階段先嵌 README，還是先加旁白。

## Phased roadmap

### Phase 1

- Outcome: 兩支可靜音的英文影片檔存在（短循環 + 完整發表）。主線、Telegram 身分、設定／好上手那一句都在。README 尚未改。

### Phase 2

- Outcome: 短循環出現在 README（取代或蓋過 `demo.gif`）。對外可以貼完整版。

### Phase 3

- Outcome: 完整發表有英文旁白；短循環仍可靜音。旁白來源（錄音或 TTS）到那一階段再決定。

### Phase 4

- Outcome: 若還要給繁中觀眾，再出對應語言版本。不是這次成功條件。

## References

- 現有 bot：`@F1_Infomation_bot`
- 現有展示：`docs/demo.gif`
- 質感參考（假設）：Linear / Raycast 那類短發表片
