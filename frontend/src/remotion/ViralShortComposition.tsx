import React from "react";
import {
  AbsoluteFill,
  Video,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { ShortClipData } from "../lib/types";
import { BeatSyncCamera } from "./components/BeatSyncCamera";
import { GlowingCaptions } from "./components/GlowingCaptions";
import { MemeOverlayLayer } from "./components/MemeOverlayLayer";
import { NarrativeNote } from "./components/NarrativeNote";
import { TopHookBanner } from "./components/TopHookBanner";

export interface ViralShortCompositionProps extends Record<string, unknown> {
  clip: ShortClipData;
}

/**
 * Master 1080x1920 @ 60fps 9:16 Viral Short Composition:
 * - Top ~240px crisp white Strykeditz-style curiosity hook banner
 * - Beat-synced camera shake, exposure flash, and punch-in zoom
 * - 8K HDR color-graded 9:16 gameplay video + optional glowing Streamer Facecam PiP
 * - Dual kinetic captions (Glowing Word-by-Word + Firefly *NARRATIVE ANNOTATIONS*)
 * - Automated GTA Meme & Freeze-Frame overlays + subtle beat-synced audio spectrum
 */
export const ViralShortComposition: React.FC<ViralShortCompositionProps> = ({
  clip,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  // Beat pulse energy for subtle bottom HUD visualizer & PiP border glow
  let beatEnergy = 0.15;
  for (let i = 0; i < clip.beats.length; i++) {
    const dt = currentTime - clip.beats[i].time;
    if (dt >= 0 && dt < 0.28) {
      const decay = 1 - dt / 0.28;
      beatEnergy = Math.max(beatEnergy, decay * clip.beats[i].strength);
    }
  }

  const bars = 18;
  const hasVideo = Boolean(clip.video_url && clip.video_url.length > 0);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#06060b",
        overflow: "hidden",
      }}
    >
      {/* 1. Main Gameplay Frame inside Beat-Synced Camera Rig */}
      <BeatSyncCamera
        beats={clip.beats}
        memes={clip.memes}
        preset={clip.preset}
      >
        {hasVideo ? (
          <Video
            src={clip.video_url}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
            crossOrigin="anonymous"
          />
        ) : (
          /* Fallback Vice City Neon Canvas when previewed without video URL */
          <AbsoluteFill
            style={{
              background: `radial-gradient(circle at ${50 + Math.sin(currentTime * 1.3) * 18}% ${45 + Math.cos(currentTime) * 12}%, rgba(255,46,147,0.45) 0%, rgba(16,10,36,0.92) 48%, rgba(4,12,24,1) 100%)`,
            }}
          />
        )}
      </BeatSyncCamera>

      {/* 2. Optional Streamer Facecam PiP Rounded Box with Neon Border */}
      {clip.facecam?.detected && (
        <div
          style={{
            position: "absolute",
            top: 274,
            left: clip.facecam.corner.includes("left") ? 36 : undefined,
            right: clip.facecam.corner.includes("right") ? 36 : undefined,
            width: 248,
            height: 248,
            borderRadius: 26,
            overflow: "hidden",
            border: `4px solid ${beatEnergy > 0.65 ? "#00F5FF" : "#FF2E93"}`,
            boxShadow: `0 12px 32px rgba(0,0,0,0.72), 0 0 ${16 + beatEnergy * 24}px ${
              beatEnergy > 0.65
                ? "rgba(0,245,255,0.75)"
                : "rgba(255,46,147,0.65)"
            }`,
            backgroundColor: "#0c0c18",
            zIndex: 28,
          }}
        >
          {hasVideo ? (
            <Video
              src={clip.video_url}
              muted
              style={{
                width: "240%",
                height: "240%",
                objectFit: "cover",
                objectPosition:
                  clip.facecam.corner === "top_left"
                    ? "0% 0%"
                    : clip.facecam.corner === "bottom_left"
                    ? "0% 100%"
                    : clip.facecam.corner === "bottom_right"
                    ? "100% 100%"
                    : "100% 0%",
              }}
              crossOrigin="anonymous"
            />
          ) : null}
          <div
            style={{
              position: "absolute",
              bottom: 10,
              left: 12,
              padding: "3px 10px",
              borderRadius: 999,
              backgroundColor: "rgba(255, 42, 95, 0.92)",
              color: "#ffffff",
              fontFamily: 'var(--font-montserrat), sans-serif',
              fontWeight: 900,
              fontSize: 16,
              letterSpacing: "0.1em",
            }}
          >
            LIVE CAM
          </div>
        </div>
      )}

      {/* 3. Top Crisp White Curiosity Hook Banner (~240px) */}
      <TopHookBanner
        text={clip.hook_banner_text}
        preset={clip.preset}
        bpm={clip.bpm}
      />

      {/* 4. Firefly-Style *NARRATIVE ANNOTATIONS* */}
      <NarrativeNote annotations={clip.annotations} />

      {/* 5. Automated GTA Meme & Freeze-Frame Overlays */}
      <MemeOverlayLayer memes={clip.memes} />

      {/* 6. Glowing Word-by-Word Kinetic Captions */}
      <GlowingCaptions captions={clip.captions} />

      {/* 7. Subtle Bottom Beat-Synced Neon Spectrum & Track Tag */}
      <div
        style={{
          position: "absolute",
          bottom: 58,
          left: 52,
          right: 52,
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          zIndex: 30,
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            padding: "8px 18px",
            borderRadius: 999,
            backgroundColor: "rgba(7, 7, 16, 0.72)",
            border: "1px solid rgba(255, 255, 255, 0.18)",
            color: "#E2E8F0",
            fontFamily: 'var(--font-montserrat), sans-serif',
            fontWeight: 700,
            fontSize: 22,
            letterSpacing: "0.04em",
          }}
        >
          ♪ {clip.bgm_title} • {Math.round(clip.bpm)} BPM
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            gap: 5,
            height: 44,
          }}
        >
          {Array.from({ length: bars }).map((_, idx) => {
            const wave =
              0.35 +
              0.65 *
                Math.abs(
                  Math.sin(currentTime * 9.5 + idx * 0.65) *
                    (0.45 + beatEnergy * 0.9)
                );
            const h = Math.max(8, Math.round(wave * 42));
            const color = idx % 2 === 0 ? "#00F5FF" : "#FF2E93";
            return (
              <div
                key={idx}
                style={{
                  width: 7,
                  height: h,
                  borderRadius: 4,
                  backgroundColor: color,
                  boxShadow: `0 0 10px ${color}`,
                  opacity: interpolate(beatEnergy, [0.15, 1], [0.55, 1]),
                }}
              />
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
