import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { next, remind, start } from "./copy";
import { clamp, flickEase, flickY, progress } from "./motion";
import { NextPanel } from "./panels/NextPanel";
import { RemindPanel } from "./panels/RemindPanel";
import { StartPanel } from "./panels/StartPanel";
import { FLICK, FULL_SEQ, PLANE, RISE } from "./timings";
import { Stage } from "./ui/Stage";
import { TelegramThread, ThreadPanel } from "./ui/TelegramChat";

const nextFrom = FULL_SEQ.start - FLICK;
const remindFrom = nextFrom + FULL_SEQ.next - FLICK;
const flick1 = nextFrom;
const flick2 = remindFrom;
const planeFrom = remindFrom + FULL_SEQ.remind - PLANE;

export const ThreadAct: React.FC = () => {
  const frame = useCurrentFrame();
  const rise = progress(frame, 0, RISE);
  const f1 = progress(frame, flick1, FLICK, flickEase);
  const f2 = progress(frame, flick2, FLICK, flickEase);
  const leave = progress(frame, planeFrom, PLANE);

  const startY = frame < flick1 ? 0 : flickY(f1, "out");
  const nextY =
    frame < flick1
      ? flickY(0, "in")
      : frame < flick2
        ? flickY(f1, "in")
        : flickY(f2, "out");
  const remindY = frame < flick2 ? flickY(0, "in") : flickY(f2, "in");

  const head =
    frame < flick1 + FLICK / 2 ? start : frame < flick2 + FLICK / 2 ? next : remind;

  return (
    <AbsoluteFill
      style={{
        opacity: interpolate(
          frame,
          [planeFrom + 4, planeFrom + PLANE],
          [1, 0],
          clamp,
        ),
        transform: `translateY(${interpolate(leave, [0, 1], [0, -36])}px)`,
      }}
    >
      <Stage
        label={head.label}
        headline={head.headline}
        labelOpacity={interpolate(rise, [0, 1], [0.35, 1])}
      >
        <div
          style={{
            opacity: rise,
            transform: `translateY(${interpolate(rise, [0, 1], [220, 0])}px)`,
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
              durationInFrames={FULL_SEQ.remind}
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
