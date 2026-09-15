import { colors } from "../launch/theme";
import {
  BEZEL,
  ISLAND_H,
  ISLAND_TOP,
  ISLAND_W,
  PHONE_H,
  PHONE_LEFT,
  PHONE_RADIUS,
  PHONE_TOP,
  PHONE_W,
} from "./layout";

export const Phone: React.FC<{
  readonly children: React.ReactNode;
}> = ({ children }) => {
  return (
    <div
      style={{
        backgroundColor: "#111318",
        borderRadius: PHONE_RADIUS,
        boxShadow: "0 32px 90px rgba(0, 0, 0, 0.55)",
        height: PHONE_H,
        left: PHONE_LEFT,
        overflow: "hidden",
        position: "absolute",
        top: PHONE_TOP,
        width: PHONE_W,
      }}
    >
      <div
        style={{
          backgroundColor: colors.surface,
          borderRadius: PHONE_RADIUS - BEZEL,
          bottom: BEZEL,
          left: BEZEL,
          overflow: "hidden",
          position: "absolute",
          right: BEZEL,
          top: BEZEL,
        }}
      >
        {children}
      </div>
      <div
        style={{
          backgroundColor: colors.text,
          borderRadius: 999,
          height: ISLAND_H,
          left: "50%",
          marginLeft: -ISLAND_W / 2,
          opacity: 0.92,
          position: "absolute",
          top: ISLAND_TOP,
          width: ISLAND_W,
          zIndex: 6,
        }}
      />
    </div>
  );
};
