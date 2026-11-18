import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { BeatMarker, MemeCue, StylePreset } from "../../lib/types";

interface BeatSyncCameraProps {
  beats: BeatMarker[];
  memes: MemeCue[];
  preset: StylePreset;
  children: React.ReactNode;
}

/**
 * Beat-Synced Camera & Exposure Engine (driven by librosa beat & bass-drop timestamps):
 * - Camera Shake: damped rotational + X/Y micro-shake (±12px, ±1.5deg, decaying over 8 frames)
 * - Exposure / White Flash: brightness(1.85) decaying back to 1.0 over 6 frames
 * - Punch-In Zoom: smooth spring scale punch (1.0 -> 1.12) + subtle dynamic drift tracking
 */
export const BeatSyncCamera: React.FC<BeatSyncCameraProps> = ({
  beats,
  memes,
  preset,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Base subtle zoom-pan tracking (starts slightly scaled > 1.05 so shakes never expose black borders)
  const progress = frame / Math.max(1, durationInFrames);
  const ambientZoom = 1.06 + 0.03 * Math.sin(progress * Math.PI * 2);
  const ambientPanX = Math.sin(progress * Math.PI * 3) * 10;
  const ambientPanY = Math.cos(progress * Math.PI * 2) * 8;

  // Locate most recent beat and most recent heavy drop (or Vine Boom meme hit)
  let dropDelta = 999;
  let dropStrength = 0;
  let beatDelta = 999;

  for (let i = 0; i < beats.length; i++) {
    const b = beats[i];
    const bFrame = Math.round(b.time * fps);
    const dt = frame - bFrame;
    if (dt >= 0) {
      if (dt < beatDelta) {
        beatDelta = dt;
      }
      if (b.is_drop && dt < dropDelta) {
        dropDelta = dt;
        dropStrength = b.strength;
      }
    }
  }

  // Meme impacts also trigger punchy camera shake + zoom
  for (let i = 0; i < memes.length; i++) {
    const m = memes[i];
    const mFrame = Math.round(m.time * fps);
    const dt = frame - mFrame;
    if (dt >= 0 && dt < dropDelta) {
      dropDelta = dt;
      dropStrength = Math.max(dropStrength, m.intensity);
    }
  }

  const presetIntensity =
    preset === "firefly_cinematic" ? 0.65 : preset === "chaotic_meme" ? 1.1 : 1.0;

  // 1. Damped rotational + X/Y camera shake (±12px, ±1.5deg, decaying over 8 frames)
  let shakeX = 0;
  let shakeY = 0;
  let shakeRot = 0;
  if (dropDelta <= 10) {
    const decay = interpolate(dropDelta, [0, 8, 10], [1, 0.08, 0], {
      extrapolateRight: "clamp",
    });
    const amp = decay * Math.max(0.7, dropStrength) * presetIntensity;
    // Deterministic high-frequency shake pattern per frame
    shakeX = Math.sin(dropDelta * 2.75 + 0.4) * 12 * amp;
    shakeY = Math.cos(dropDelta * 3.4 + 1.1) * 12 * amp;
    shakeRot = Math.sin(dropDelta * 2.2) * 1.5 * amp;
  }

  // 2. Exposure / White Flash: instant brightness(1.85) decaying back to 1.0 over 6 frames
  let brightness = 1.0;
  let flashOpacity = 0;
  if (dropDelta <= 6) {
    const maxBright = 1.0 + 0.85 * presetIntensity; // 1.85 at full strength
    brightness = interpolate(dropDelta, [0, 6], [maxBright, 1.0], {
      extrapolateRight: "clamp",
    });
    flashOpacity = interpolate(dropDelta, [0, 6], [0.34 * presetIntensity, 0], {
      extrapolateRight: "clamp",
    });
  } else if (beatDelta <= 4) {
    brightness = interpolate(beatDelta, [0, 4], [1.14, 1.0], {
      extrapolateRight: "clamp",
    });
  }

  // 3. Punch-In Zoom: smooth spring scale punch (1.0 -> 1.12) on drops, micro-pulse on regular beats
  let punchScale = 1.0;
  if (dropDelta <= 22) {
    const sp = spring({
      frame: dropDelta,
      fps,
      config: { damping: 11, stiffness: 260, mass: 0.65 },
    });
    // Quick snap up to 1.12 then settle back to 1.0
    const decayOut = interpolate(dropDelta, [0, 4, 22], [1, 1, 0], {
      extrapolateRight: "clamp",
    });
    punchScale = 1.0 + 0.12 * sp * decayOut * presetIntensity;
  } else if (beatDelta <= 8) {
    punchScale = interpolate(beatDelta, [0, 2, 8], [1.0, 1.035, 1.0], {
      extrapolateRight: "clamp",
    });
  }

  const totalScale = ambientZoom * punchScale;

  // Check if a freeze-frame meme is currently active
  const activeFreezeMeme = memes.find((m) => {
    const startF = Math.round(m.time * fps);
    const endF = Math.round((m.time + m.duration) * fps);
    return m.freeze_frame && frame >= startF && frame <= endF;
  });

  const freezeDesat = activeFreezeMeme
    ? activeFreezeMeme.type === "gta_wasted_overlay"
      ? "saturate(0.22) contrast(1.25)"
      : "saturate(0.65) contrast(1.18)"
    : "contrast(1.06) saturate(1.1)";

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        backgroundColor: "#05050a",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: `translate3d(${ambientPanX + shakeX}px, ${ambientPanY + shakeY}px, 0) scale(${totalScale}) rotate(${shakeRot}deg)`,
          transformOrigin: "center center",
          filter: `brightness(${brightness.toFixed(3)}) ${freezeDesat}`,
          willChange: "transform, filter",
        }}
      >
        {children}
      </div>

      {/* Additive Beat-Drop Exposure White Flash Bloom */}
      {flashOpacity > 0.01 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            background:
              "radial-gradient(circle at 50% 48%, rgba(255,255,255,0.95) 0%, rgba(255,220,245,0.45) 55%, rgba(0,240,255,0.18) 100%)",
            opacity: flashOpacity,
            mixBlendMode: "screen",
            zIndex: 18,
          }}
        />
      )}

      {/* Vice City Subtle Neon Vignette & HDR Edge Sheen */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          background:
            "radial-gradient(ellipse at center, rgba(0,0,0,0) 56%, rgba(10,4,22,0.58) 100%)",
          zIndex: 12,
        }}
      />
    </div>
  );
};
