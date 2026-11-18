import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { MemeCue } from "../../lib/types";

interface MemeOverlayLayerProps {
  memes: MemeCue[];
}

export const MemeOverlayLayer: React.FC<MemeOverlayLayerProps> = ({
  memes,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  const activeMemes = memes.filter(
    (m) => currentTime >= m.time && currentTime <= m.time + m.duration
  );

  if (!activeMemes.length) return null;

  return (
    <>
      {activeMemes.map((meme) => {
        const startFrame = Math.round(meme.time * fps);
        const totalFrames = Math.max(12, Math.round(meme.duration * fps));
        const relFrame = Math.max(0, frame - startFrame);
        const framesLeft = Math.max(0, startFrame + totalFrames - frame);

        const slam = spring({
          frame: relFrame,
          fps,
          config: { damping: 10, stiffness: 280, mass: 0.6 },
        });
        const fadeOut = interpolate(framesLeft, [0, 10], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        if (meme.type === "gta_wasted_overlay") {
          const scale = interpolate(slam, [0, 1], [1.75, 1.0]);
          return (
            <div
              key={meme.id}
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 38,
                pointerEvents: "none",
                opacity: fadeOut,
              }}
            >
              {/* Dark cinematic GTA WASTED horizontal band */}
              <div
                style={{
                  width: "100%",
                  padding: "46px 0",
                  background:
                    "linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(10,8,12,0.86) 20%, rgba(10,8,12,0.92) 80%, rgba(0,0,0,0) 100%)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  transform: `scale(${scale})`,
                }}
              >
                <div
                  style={{
                    fontFamily:
                      'var(--font-anton), "Impact", "Arial Black", sans-serif',
                    fontSize: 138,
                    letterSpacing: "0.08em",
                    color: "#E11D48",
                    WebkitTextStroke: "4px #000000",
                    textShadow:
                      "0 0 36px rgba(225, 29, 72, 0.9), 0 8px 0 #000000, -4px 0 0 rgba(0,240,255,0.65)",
                  }}
                >
                  WASTED
                </div>
                <div
                  style={{
                    marginTop: 6,
                    fontFamily: 'var(--font-montserrat), sans-serif',
                    fontWeight: 800,
                    fontSize: 28,
                    letterSpacing: "0.24em",
                    color: "#E2E8F0",
                    textTransform: "uppercase",
                  }}
                >
                  VICE CITY HOSPITAL BILL: $5,000
                </div>
              </div>
            </div>
          );
        }

        if (meme.type === "police_siren_flash") {
          const isRed = Math.floor(relFrame / 5) % 2 === 0;
          return (
            <div
              key={meme.id}
              style={{
                position: "absolute",
                inset: 0,
                pointerEvents: "none",
                zIndex: 36,
                opacity: fadeOut,
              }}
            >
              {/* Alternating Red/Blue Siren Edge Strobe */}
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  boxShadow: isRed
                    ? "inset 0 0 140px rgba(255, 24, 68, 0.72)"
                    : "inset 0 0 140px rgba(0, 140, 255, 0.75)",
                }}
              />
              {/* GTA 5-Star Wanted Level HUD */}
              <div
                style={{
                  position: "absolute",
                  top: 270,
                  right: 46,
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "10px 22px",
                  borderRadius: 14,
                  backgroundColor: "rgba(6, 8, 18, 0.78)",
                  border: `2px solid ${isRed ? "#ff2a5f" : "#00a6ff"}`,
                  transform: `scale(${interpolate(slam, [0, 1], [0.7, 1])})`,
                }}
              >
                <span
                  style={{
                    fontSize: 40,
                    letterSpacing: "0.08em",
                    color: isRed ? "#FF2A5F" : "#38BDF8",
                    textShadow: isRed
                      ? "0 0 18px rgba(255,42,95,0.9)"
                      : "0 0 18px rgba(56,189,248,0.9)",
                  }}
                >
                  ★★★★★
                </span>
              </div>
            </div>
          );
        }

        if (meme.type === "mission_passed") {
          const scale = interpolate(slam, [0, 1], [1.4, 1.0]);
          return (
            <div
              key={meme.id}
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                pointerEvents: "none",
                zIndex: 38,
                opacity: fadeOut,
              }}
            >
              <div
                style={{
                  padding: "32px 64px",
                  borderRadius: 24,
                  background: "rgba(6, 6, 12, 0.84)",
                  border: "3px solid #FACC15",
                  boxShadow: "0 0 55px rgba(250, 204, 21, 0.55)",
                  textAlign: "center",
                  transform: `scale(${scale})`,
                }}
              >
                <div
                  style={{
                    fontFamily: 'var(--font-anton), "Impact", sans-serif',
                    fontSize: 88,
                    color: "#FACC15",
                    letterSpacing: "0.05em",
                    WebkitTextStroke: "3px #000",
                    textShadow: "0 0 26px rgba(250, 204, 21, 0.85)",
                  }}
                >
                  MISSION PASSED!
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-montserrat), sans-serif',
                    fontWeight: 900,
                    fontSize: 40,
                    color: "#FFFFFF",
                    letterSpacing: "0.14em",
                    marginTop: 6,
                  }}
                >
                  RESPECT +999
                </div>
              </div>
            </div>
          );
        }

        if (meme.type === "zoom_freeze_frame") {
          const scale = interpolate(slam, [0, 1], [1.35, 1.0]);
          return (
            <div
              key={meme.id}
              style={{
                position: "absolute",
                inset: 0,
                pointerEvents: "none",
                zIndex: 37,
                opacity: fadeOut,
              }}
            >
              <div
                style={{
                  position: "absolute",
                  inset: 34,
                  top: 266,
                  border: "6px dashed rgba(255, 230, 0, 0.85)",
                  borderRadius: 28,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  top: "44%",
                  left: "50%",
                  transform: `translate(-50%, -50%) scale(${scale}) rotate(-6deg)`,
                  backgroundColor: "#FFE600",
                  color: "#09090d",
                  padding: "16px 36px",
                  borderRadius: 14,
                  border: "5px solid #000000",
                  boxShadow: "0 14px 40px rgba(0,0,0,0.7)",
                  fontFamily: 'var(--font-anton), "Impact", sans-serif',
                  fontSize: 66,
                  letterSpacing: "0.05em",
                  textTransform: "uppercase",
                }}
              >
                {meme.label || "HOLD UP..."}
              </div>
            </div>
          );
        }

        if (meme.type === "skull_reaction") {
          const popScale = interpolate(slam, [0, 1], [0.2, 1.15]);
          return (
            <div
              key={meme.id}
              style={{
                position: "absolute",
                top: 470,
                right: 64,
                zIndex: 37,
                pointerEvents: "none",
                opacity: fadeOut,
                transform: `scale(${popScale}) rotate(8deg)`,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <div
                style={{
                  fontSize: 130,
                  filter: "drop-shadow(0 12px 24px rgba(0,0,0,0.85))",
                }}
              >
                💀
              </div>
              <div
                style={{
                  marginTop: -8,
                  padding: "6px 18px",
                  borderRadius: 10,
                  backgroundColor: "#09090d",
                  border: "2px solid #ff2e93",
                  color: "#ffffff",
                  fontFamily: 'var(--font-montserrat), sans-serif',
                  fontWeight: 900,
                  fontSize: 28,
                  letterSpacing: "0.08em",
                }}
              >
                {meme.label || "COOKED"}
              </div>
            </div>
          );
        }

        // Default: vine_boom_shockwave expanding radial ring
        const ringScale = interpolate(relFrame, [0, 24], [0.35, 2.3], {
          extrapolateRight: "clamp",
        });
        const ringOpacity = interpolate(relFrame, [0, 24], [0.9, 0], {
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={meme.id}
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              pointerEvents: "none",
              zIndex: 36,
            }}
          >
            <div
              style={{
                width: 420,
                height: 420,
                borderRadius: "50%",
                border: "14px solid #00F5FF",
                boxShadow:
                  "0 0 60px rgba(0,245,255,0.9), inset 0 0 60px rgba(255,46,147,0.7)",
                transform: `scale(${ringScale})`,
                opacity: ringOpacity,
              }}
            />
          </div>
        );
      })}
    </>
  );
};
