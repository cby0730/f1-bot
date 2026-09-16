import { interpolate, useCurrentFrame } from "remotion";
import { inter } from "../fonts";
import { clamp, easeOut } from "../motion";
import { colors } from "../theme";

const TITLE_STACK_H = 168;
const TITLE_TRAVEL = 40;

type TitleCopy = {
  readonly label: string;
  readonly headline: string;
};

const TitleCopyView: React.FC<TitleCopy> = ({ label, headline }) => (
  <>
    <div
      style={{
        color: colors.label,
        fontSize: 26,
        fontWeight: 600,
        letterSpacing: 4,
        textTransform: "uppercase",
      }}
    >
      {label}
    </div>
    <div
      style={{
        color: colors.text,
        fontSize: 64,
        fontWeight: 800,
        letterSpacing: -1.6,
        lineHeight: 1.2,
        marginTop: 12,
        paddingBottom: 6,
      }}
    >
      {headline}
    </div>
  </>
);

export const Stage: React.FC<{
  readonly label: string;
  readonly headline: string;
  readonly incoming?: TitleCopy;
  readonly swap?: number;
  readonly swapDirection?: "up" | "down";
  readonly children?: React.ReactNode;
  readonly labelOpacity?: number;
  readonly bgOpacity?: number;
}> = ({
  label,
  headline,
  incoming,
  swap = 0,
  swapDirection = "down",
  children,
  labelOpacity,
  bgOpacity = 1,
}) => {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [0, 6], [0, 1], { ...clamp, easing: easeOut });
  const swapping = incoming !== undefined;
  const sign = swapDirection === "down" ? 1 : -1;
  const outOp = interpolate(swap, [0, 0.55], [1, 0], clamp);
  const inOp = interpolate(swap, [0.35, 1], [0, 1], clamp);

  return (
    <div
      style={{
        backgroundColor:
          bgOpacity >= 1 ? colors.bg : `rgba(7, 8, 12, ${bgOpacity})`,
        display: "flex",
        flexDirection: "column",
        fontFamily: inter,
        height: "100%",
        padding: "64px 100px 56px",
        width: "100%",
      }}
    >
      <div
        style={{
          height: swapping ? TITLE_STACK_H : undefined,
          opacity: labelOpacity ?? enter,
          overflow: swapping ? "hidden" : undefined,
          position: swapping ? "relative" : undefined,
        }}
      >
        {swapping ? (
          <>
            <div
              style={{
                left: 0,
                opacity: outOp,
                position: "absolute",
                right: 0,
                top: 0,
                transform: `translateY(${swap * TITLE_TRAVEL * sign}px)`,
              }}
            >
              <TitleCopyView label={label} headline={headline} />
            </div>
            <div
              style={{
                left: 0,
                opacity: inOp,
                position: "absolute",
                right: 0,
                top: 0,
                transform: `translateY(${(swap - 1) * TITLE_TRAVEL * sign}px)`,
              }}
            >
              <TitleCopyView label={incoming.label} headline={incoming.headline} />
            </div>
          </>
        ) : (
          <TitleCopyView label={label} headline={headline} />
        )}
      </div>
      <div
        style={{
          alignItems: "center",
          display: "flex",
          flex: 1,
          justifyContent: "center",
          minHeight: 0,
        }}
      >
        {children}
      </div>
    </div>
  );
};
