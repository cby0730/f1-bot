import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { next, remind, start } from "./copy";
import { flickEase, flickY, progress } from "./motion";
import { NextPanel } from "./panels/NextPanel";
import { RemindPanel } from "./panels/RemindPanel";
import { StartPanel } from "./panels/StartPanel";
import { FLICK, FULL_SEQ, HOLD, RISE } from "./timings";
import { Stage } from "./ui/Stage";
import { TelegramThread, ThreadPanel } from "./ui/TelegramChat";

const nextFrom = FULL_SEQ.start - FLICK;
const remindFrom = nextFrom + FULL_SEQ.next - FLICK;
const flick1 = nextFrom;
const flick2 = remindFrom;

export const ThreadAct: React.FC = () => {
  const frame = useCurrentFrame();
  const rise = progress(frame, 8, RISE - 8);
  const f1 = progress(frame, flick1, FLICK, flickEase);
  const f2 = progress(frame, flick2, FLICK, flickEase);

  const startY = frame < flick1 ? 0 : flickY(f1, "out", "down");
  const nextY =
    frame < flick1
      ? flickY(0, "in", "down")
      : frame < flick2
        ? flickY(f1, "in", "down")
        : flickY(f2, "out", "up");
  const remindY = frame < flick2 ? flickY(0, "in", "up") : flickY(f2, "in", "up");

  const head =
    frame < flick1 + FLICK / 2 ? start : frame < flick2 + FLICK / 2 ? next : remind;

  return (
    <AbsoluteFill>
      <Stage
        bgOpacity={rise}
        label={head.label}
        headline={head.headline}
        labelOpacity={interpolate(rise, [0, 1], [0, 1])}
      >
        <div
          style={{
            opacity: rise,
            transform: `scale(${interpolate(rise, [0, 1], [0.84, 1])})`,
            transformOrigin: "50% 0%",
          }}
        >
          <TelegramThread>
            <Sequence durationInFrames={FULL_SEQ.start} layout="none" name="Start">
              <ThreadPanel y={startY}>
                <StartPanel />
              </ThreadPanel>
            </Sequence>
            <Sequence
              durationInFrames={FULL_SEQ.next}
              from={nextFrom}
              layout="none"
              name="Next"
            >
              <ThreadPanel y={nextY}>
                <NextPanel />
              </ThreadPanel>
            </Sequence>
            <Sequence
              durationInFrames={HOLD.remind}
              from={remindFrom}
              layout="none"
              name="Remind"
            >
              <ThreadPanel y={remindY}>
                <RemindPanel />
              </ThreadPanel>
            </Sequence>
          </TelegramThread>
        </div>
      </Stage>
    </AbsoluteFill>
  );
};
