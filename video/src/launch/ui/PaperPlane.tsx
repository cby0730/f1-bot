/** Flat white dart. The motion is the cut, not the material. */

export const PaperPlane: React.FC<{
  readonly width?: number;
}> = ({ width = 1000 }) => {
  return (
    <svg
      aria-hidden="true"
      height={width * 0.55}
      viewBox="0 0 1000 550"
      width={width}
      style={{ display: "block", overflow: "visible" }}
    >
      <path d="M500 24 36 508 500 428Z" fill="#ffffff" />
      <path d="M500 24 964 508 500 428Z" fill="#e6e8ed" />
      <path d="M500 24 500 428 428 444Z" fill="#d2d5db" />
      <path d="M500 24 500 428 572 444Z" fill="#c4c8ce" />
    </svg>
  );
};
