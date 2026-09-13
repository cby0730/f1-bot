import { colors } from "../theme";

/** iOS-style Telegram tile: brand blue rounded square + paper plane. */
export const TelegramIcon: React.FC<{
  readonly size?: number;
}> = ({ size = 32 }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      style={{ display: "block", flexShrink: 0 }}
    >
      <rect width="24" height="24" rx="6.2" fill={colors.telegram} />
      <path
        fill="#ffffff"
        d="M18.55 6.08 5.86 11.1c-.86.34-.85.82.16 1.02l3.26.99 1.24 3.79c.16.48.29.67.76.67.39 0 .56-.18.78-.4l1.9-1.84 3.94 2.9c.72.4 1.25.2 1.43-.67l2.58-12.17c.26-.99-.4-1.44-1.08-1.15z"
      />
      <path
        fill="#B7E3F8"
        d="M9.55 13.28 17.2 8.2c.22-.15.4-.07.23.16l-5.55 6.95-.52 2.28z"
      />
    </svg>
  );
};
