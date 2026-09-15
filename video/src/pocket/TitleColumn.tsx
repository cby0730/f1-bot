import { interpolate, useCurrentFrame } from "remotion";
import { hook, next, remind, settings, start } from "../launch/copy";
import { clamp, easeOut, flickEase, progress } from "../launch/motion";
import { colors } from "../launch/theme";
import { inter } from "../launch/fonts";
import { TITLE_LEFT, TITLE_WIDTH } from "./layout";
import {
  AT,
  AT_SETTINGS,
  FLICK,
  FLICK1,
  FLICK2,
  RISE,
} from "./timings";

const TITLE_TRAVEL = 36;

type TitleCopy = {
  readonly kicker?: string;
  readonly title: string;
  readonly sub?: string;
  readonly hookStack?: boolean;
};

const hookCopy: TitleCopy = {
  hookStack: true,
  title: hook.headline,
};

const startCopy: TitleCopy = { kicker: start.label, title: start.headline };
const nextCopy: TitleCopy = { kicker: next.label, title: next.headline };
const remindCopy: TitleCopy = { kicker: remind.label, title: remind.headline };
const settingsCopy: TitleCopy = {
  kicker: settings.label,
  title: settings.headline,
};

const Stack: React.FC<TitleCopy & { y: number }> = ({
  hookStack,
  kicker,
  title,
  y,
}) => {
  return (
    <div
      style={{
        transform: `translateY(${y}px)`,
      }}
    >
      {hookStack ? (
        <>
          <div
            style={{
              color: colors.telegram,
              fontSize: 32,
              fontWeight: 700,
              letterSpacing: -0.4,
              whiteSpace: "nowrap",
            }}
          >
            {hook.support}
          </div>
          <div
            style={{
              color: colors.text,
              fontSize: 56,
              fontWeight: 800,
              letterSpacing: -1.6,
              lineHeight: 1.05,
              marginTop: 14,
              whiteSpace: "nowrap",
            }}
          >
            {hook.headline}
          </div>
          <div
            style={{
              color: colors.muted,
              fontSize: 22,
              fontWeight: 500,
              marginTop: 16,
              whiteSpace: "nowrap",
            }}
          >
            {hook.sub}
          </div>
        </>
      ) : (
        <>
          <div
            style={{
              color: colors.label,
              fontSize: 22,
              fontWeight: 600,
              letterSpacing: 4,
              textTransform: "uppercase",
              whiteSpace: "nowrap",
            }}
          >
            {kicker}
          </div>
          <div
            style={{
              color: colors.text,
              fontSize: 48,
              fontWeight: 800,
              letterSpacing: -1.2,
              lineHeight: 1.08,
              marginTop: 12,
              whiteSpace: "nowrap",
            }}
          >
            {title}
          </div>
        </>
      )}
    </div>
  );
};

export const TitleColumn: React.FC = () => {
  const frame = useCurrentFrame();

  let outgoing: TitleCopy = hookCopy;
  let incoming: TitleCopy = hookCopy;
  let swap = 0;
  let sign = 1;

  if (frame < AT.start) {
    outgoing = hookCopy;
    incoming = startCopy;
    swap = progress(frame, AT.start - RISE, RISE, easeOut);
    sign = 1;
  } else if (frame < FLICK1) {
    outgoing = startCopy;
    incoming = startCopy;
    swap = 1;
  } else if (frame < FLICK2) {
    outgoing = startCopy;
    incoming = nextCopy;
    swap = progress(frame, FLICK1, FLICK, flickEase);
    sign = 1;
  } else if (frame < AT_SETTINGS) {
    outgoing = nextCopy;
    incoming = remindCopy;
    swap = progress(frame, FLICK2, FLICK, flickEase);
    sign = -1;
  } else {
    outgoing = remindCopy;
    incoming = settingsCopy;
    swap = progress(frame, AT_SETTINGS, 12, easeOut);
    sign = 1;
  }

  const outOp = interpolate(swap, [0, 0.42], [1, 0], clamp);
  const inOp = interpolate(swap, [0.48, 1], [0, 1], clamp);

  return (
    <div
      style={{
        alignItems: "center",
        display: "flex",
        fontFamily: inter,
        height: 1044,
        left: TITLE_LEFT,
        overflow: "hidden",
        position: "absolute",
        top: 36,
        width: TITLE_WIDTH,
      }}
    >
      <div style={{ height: 180, position: "relative", width: "100%" }}>
        <div style={{ opacity: outOp, position: "absolute", width: "100%" }}>
          <Stack {...outgoing} y={swap * TITLE_TRAVEL * sign} />
        </div>
        <div style={{ opacity: inOp, position: "absolute", width: "100%" }}>
          <Stack {...incoming} y={(swap - 1) * TITLE_TRAVEL * sign} />
        </div>
      </div>
    </div>
  );
};
