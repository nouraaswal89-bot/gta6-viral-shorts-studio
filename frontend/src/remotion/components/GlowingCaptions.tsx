import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { WordCaption } from "../../lib/types";

interface GlowingCaptionsProps {
  captions: WordCaption[];
}

const COLOR_MAP: Record<
  WordCaption["color"],
  { fill: string; glow: string; glowOuter: string }
> = {
  yellow: {
    fill: "#FFE600",
    glow: "rgba(255, 230, 0, 0.9)",
    glowOuter: "rgba(255, 140, 0, 0.65)",
  },
  cyan: {
    fill: "#00F5FF",
    glow: "rgba(0, 245, 255, 0.95)",
    glowOuter: "rgba(0, 140, 255, 0.7)",
  },
  red: {
    fill: "#FF2A5F",
    glow: "rgba(255, 42, 95, 0.95)",
    glowOuter: "rgba(255, 0, 60, 0.72)",
  },
  white: {
    fill: "#FFFFFF",
    glow: "rgba(255, 255, 255, 0.85)",
    glowOuter: "rgba(0, 240, 255, 0.45)",
  },
};

/**
 * Glowing Word-by-Word Kinetic Captions:
 * - Montserrat ExtraBold / Burbank Big Condensed aesthetic
 * - Active spoken word pops with spring() scale (1.0 -> 1.18)
 * - Bright yellow/cyan/red fill, thick black stroke, multi-layered neon outer drop-shadow
 */
export const GlowingCaptions: React.FC<GlowingCaptionsProps> = ({
  captions,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  if (!captions.length) return null;

  // Group into punchy 3-word Gen-Z caption chunks
  const chunkSize = 3;
  let activeChunkIndex = -1;
  let activeWordGlobalIdx = -1;

  for (let i = 0; i < captions.length; i++) {
    const c = captions[i];
    if (currentTime >= c.start && currentTime <= c.end + 0.14) {
      activeWordGlobalIdx = i;
      activeChunkIndex = Math.floor(i / chunkSize);
      break;
    }
  }

  // Keep showing the chunk briefly between consecutive words inside the same chunk
  if (activeChunkIndex === -1) {
    for (let cIdx = 0; cIdx < Math.ceil(captions.length / chunkSize); cIdx++) {
      const startI = cIdx * chunkSize;
      const endI = Math.min(captions.length - 1, startI + chunkSize - 1);
      if (
        currentTime >= captions[startI].start &&
        currentTime <= captions[endI].end + 0.12
      ) {
        activeChunkIndex = cIdx;
        break;
      }
    }
  }

  if (activeChunkIndex === -1) return null;

  const chunkStart = activeChunkIndex * chunkSize;
  const chunk = captions.slice(chunkStart, chunkStart + chunkSize);

  return (
    <div
      style={{
        position: "absolute",
        left: 44,
        right: 44,
        bottom: 290,
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        justifyContent: "center",
        gap: "14px 22px",
        zIndex: 35,
        pointerEvents: "none",
      }}
    >
      {chunk.map((item, idx) => {
        const globalIdx = chunkStart + idx;
        const isActive = globalIdx === activeWordGlobalIdx;
        const wordStartFrame = Math.round(item.start * fps);
        const relFrame = Math.max(0, frame - wordStartFrame);

        const pop = isActive
          ? spring({
              frame: relFrame,
              fps,
              config: { damping: 10, stiffness: 320, mass: 0.55 },
            })
          : 0;

        // Exact 1.0 -> 1.18 spring pop on active spoken word
        const scale = isActive ? 1.0 + 0.18 * pop : 0.96;
        const palette = COLOR_MAP[item.color] || COLOR_MAP.yellow;
        const fill = isActive ? palette.fill : "#FFFFFF";

        const dropShadow = isActive
          ? `drop-shadow(0 6px 0 #000000) drop-shadow(0 0 18px ${palette.glow}) drop-shadow(0 0 38px ${palette.glowOuter})`
          : "drop-shadow(0 5px 0 #000000) drop-shadow(0 0 10px rgba(0,0,0,0.85))";

        return (
          <span
            key={`${globalIdx}_${item.word}`}
            style={{
              display: "inline-block",
              fontFamily:
                'var(--font-anton), var(--font-montserrat), "Impact", sans-serif',
              fontWeight: 900,
              fontSize: item.emphasis && isActive ? 94 : 84,
              lineHeight: 1.02,
              letterSpacing: "0.02em",
              textTransform: "uppercase",
              color: fill,
              WebkitTextStroke: "5px #000000",
              paintOrder: "stroke fill",
              transform: `scale(${scale}) rotate(${isActive ? (globalIdx % 2 === 0 ? -1.4 : 1.4) : 0}deg)`,
              filter: dropShadow,
              transition: "color 60ms linear",
            }}
          >
            {item.word}
          </span>
        );
      })}
    </div>
  );
};
