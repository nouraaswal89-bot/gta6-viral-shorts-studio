import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { StylePreset } from "../../lib/types";

interface TopHookBannerProps {
  text: string;
  preset: StylePreset;
  bpm: number;
}

export const TopHookBanner: React.FC<TopHookBannerProps> = ({
  text,
  preset,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 220, mass: 0.7 },
  });

  const translateY = interpolate(entrance, [0, 1], [-48, 0]);
  const textScale = interpolate(entrance, [0, 1], [0.92, 1]);

  // Dynamic font size so 1-2 lines always look tight, bold, and crisp inside ~240px bar
  const len = text.trim().length;
  const fontSize = len <= 28 ? 58 : len <= 42 ? 50 : 44;

  const accentGradient =
    preset === "firefly_cinematic"
      ? "linear-gradient(90deg, #ff8a3d 0%, #ff2e93 50%, #00f0ff 100%)"
      : preset === "chaotic_meme"
      ? "linear-gradient(90deg, #ffd43b 0%, #ff2e93 50%, #ffd43b 100%)"
      : "linear-gradient(90deg, #ff2e93 0%, #00f0ff 50%, #ff2e93 100%)";

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        height: 240,
        backgroundColor: "#ffffff",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px 44px 18px 44px",
        zIndex: 40,
        boxShadow: "0 14px 42px rgba(0, 0, 0, 0.55)",
        transform: `translateY(${translateY}px)`,
      }}
    >
      <div
        style={{
          color: "#09090d",
          fontFamily:
            'var(--font-montserrat), "Montserrat", "Arial Black", sans-serif',
          fontWeight: 900,
          fontSize,
          lineHeight: 1.08,
          letterSpacing: "-0.035em",
          textAlign: "center",
          textTransform: "uppercase",
          transform: `scale(${textScale})`,
          wordBreak: "break-word",
          maxWidth: "100%",
        }}
      >
        {text}
      </div>

      {/* Subtle razor-thin Vice City neon separator */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 6,
          background: accentGradient,
        }}
      />
    </div>
  );
};
