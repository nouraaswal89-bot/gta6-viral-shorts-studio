import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { NarrativeAnnotation } from "../../lib/types";

interface NarrativeNoteProps {
  annotations: NarrativeAnnotation[];
}

/**
 * Firefly-Style Narrative Annotations:
 * Uppercase italicized micro-captions (*INSTANT REGRET*, *POLICE SURROUNDED HIM*, *WAIT FOR IT...*)
 * timed to key visual beats.
 */
export const NarrativeNote: React.FC<NarrativeNoteProps> = ({
  annotations,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  const active = annotations.find(
    (a) => currentTime >= a.start && currentTime <= a.end
  );
  if (!active) return null;

  const startFrame = Math.round(active.start * fps);
  const endFrame = Math.round(active.end * fps);
  const relFrame = Math.max(0, frame - startFrame);
  const framesLeft = Math.max(0, endFrame - frame);

  const popIn = spring({
    frame: relFrame,
    fps,
    config: { damping: 14, stiffness: 210, mass: 0.7 },
  });

  const fadeOut = interpolate(framesLeft, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const translateY = interpolate(popIn, [0, 1], [18, 0]);
  const topPosition =
    active.position === "middle"
      ? 900
      : active.position === "lower"
      ? 1350
      : 315;

  return (
    <div
      style={{
        position: "absolute",
        top: topPosition,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
        zIndex: 34,
        opacity: Math.min(popIn, fadeOut),
        transform: `translateY(${translateY}px)`,
      }}
    >
      <div
        style={{
          padding: "12px 30px",
          borderRadius: 999,
          backgroundColor: "rgba(7, 7, 15, 0.68)",
          border: "1.5px solid rgba(255, 255, 255, 0.25)",
          backdropFilter: "blur(8px)",
          boxShadow:
            "0 8px 30px rgba(0, 0, 0, 0.55), 0 0 24px rgba(0, 240, 255, 0.25)",
        }}
      >
        <span
          style={{
            fontFamily:
              'var(--font-montserrat), "Montserrat", sans-serif',
            fontWeight: 800,
            fontStyle: "italic",
            fontSize: 34,
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            color: "#F8FAFC",
            textShadow:
              "0 2px 12px rgba(0, 240, 255, 0.65), 0 2px 4px rgba(0,0,0,0.9)",
          }}
        >
          {active.text}
        </span>
      </div>
    </div>
  );
};
