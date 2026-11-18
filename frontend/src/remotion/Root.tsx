import React from "react";
import { Composition } from "remotion";
import type { ShortClipData } from "../lib/types";
import {
  ViralShortComposition,
  type ViralShortCompositionProps,
} from "./ViralShortComposition";

export const DEFAULT_PREVIEW_CLIP: ShortClipData = {
  clip_id: "preview_01",
  index: 1,
  title: "Vice Beach Ramp Jump Chaos",
  hook_banner_text: "BRO REALLY TRIED THIS IN GTA 6 💀🔥",
  viral_score: 98,
  viral_reason: "High-energy 5-star police ramp jump with bass-drop WASTED payoff.",
  emotion: "hype_phonk",
  preset: "strykeditz_phonk",
  source_start: 0,
  source_end: 18,
  duration: 18,
  fps: 60,
  width: 1080,
  height: 1920,
  video_url: "",
  audio_mix_url: null,
  bgm_url: null,
  bgm_title: "Vice City Drift Phonk",
  bpm: 130,
  rendered_mp4_url: null,
  render_status: "ready",
  facecam: {
    detected: false,
    corner: "top_right",
    x: 0.74,
    y: 0.03,
    width: 0.24,
    height: 0.24,
  },
  captions: [
    { word: "BRO", start: 0.5, end: 1.2, emphasis: true, color: "yellow" },
    { word: "REALLY", start: 1.2, end: 1.9, emphasis: false, color: "yellow" },
    { word: "SENT", start: 1.9, end: 2.6, emphasis: true, color: "cyan" },
    { word: "IT", start: 2.6, end: 3.3, emphasis: false, color: "yellow" },
    { word: "INTO", start: 3.3, end: 4.0, emphasis: false, color: "yellow" },
    { word: "FIVE", start: 4.0, end: 4.8, emphasis: true, color: "cyan" },
    { word: "STARS", start: 4.8, end: 5.7, emphasis: true, color: "red" },
    { word: "WASTED", start: 12.0, end: 14.0, emphasis: true, color: "red" },
  ],
  annotations: [
    { text: "*WAIT FOR IT...*", start: 2.0, end: 4.8, position: "upper" },
    { text: "*INSTANT REGRET*", start: 11.2, end: 14.8, position: "upper" },
  ],
  beats: [
    { time: 1.85, strength: 0.95, is_drop: true },
    { time: 3.7, strength: 0.9, is_drop: true },
    { time: 5.55, strength: 0.98, is_drop: true },
    { time: 7.4, strength: 0.88, is_drop: true },
    { time: 9.25, strength: 0.96, is_drop: true },
    { time: 11.1, strength: 0.92, is_drop: true },
    { time: 12.95, strength: 1.0, is_drop: true },
  ],
  memes: [
    {
      id: "m1",
      type: "vine_boom_shockwave",
      label: "VINE BOOM",
      time: 3.7,
      duration: 0.9,
      freeze_frame: false,
      intensity: 0.95,
    },
    {
      id: "m2",
      type: "police_siren_flash",
      label: "5-STAR WANTED",
      time: 7.4,
      duration: 2.2,
      freeze_frame: false,
      intensity: 0.9,
    },
    {
      id: "m3",
      type: "gta_wasted_overlay",
      label: "WASTED",
      time: 12.0,
      duration: 2.5,
      freeze_frame: true,
      intensity: 1.0,
    },
  ],
  speed_ramps: [{ start: 11.5, end: 13.5, speed: 0.45 }],
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="ViralShortComposition"
      component={ViralShortComposition}
      durationInFrames={1080}
      fps={60}
      width={1080}
      height={1920}
      defaultProps={{ clip: DEFAULT_PREVIEW_CLIP }}
      calculateMetadata={({ props }: { props: ViralShortCompositionProps }) => {
        const clip = props.clip || DEFAULT_PREVIEW_CLIP;
        const fps = clip.fps || 60;
        const durationSec = Math.max(15, Math.min(30, clip.duration || 18));
        return {
          fps,
          width: clip.width || 1080,
          height: clip.height || 1920,
          durationInFrames: Math.round(durationSec * fps),
        };
      }}
    />
  );
};
