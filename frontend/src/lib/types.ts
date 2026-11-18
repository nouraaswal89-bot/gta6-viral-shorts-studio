export type StylePreset =
  | "strykeditz_phonk"
  | "firefly_cinematic"
  | "chaotic_meme";

export type EmotionTag = "hype_phonk" | "funny_meme" | "epic_cinematic";

export type PipelineStageId =
  | "ingest"
  | "ai_director"
  | "music"
  | "beats_captions"
  | "enhance_fx"
  | "render";

export type StageStatus = "pending" | "running" | "completed" | "failed";

export interface PipelineStageState {
  id: PipelineStageId;
  index: number;
  label: string;
  status: StageStatus;
  progress: number;
  detail: string;
}

export interface WordCaption {
  word: string;
  start: number;
  end: number;
  emphasis: boolean;
  color: "yellow" | "cyan" | "red" | "white";
}

export interface NarrativeAnnotation {
  text: string;
  start: number;
  end: number;
  position: "upper" | "middle" | "lower";
}

export interface BeatMarker {
  time: number;
  strength: number;
  is_drop: boolean;
}

export type MemeOverlayType =
  | "gta_wasted_overlay"
  | "vine_boom_shockwave"
  | "zoom_freeze_frame"
  | "skull_reaction"
  | "police_siren_flash"
  | "mission_passed";

export interface MemeCue {
  id: string;
  type: MemeOverlayType;
  label: string;
  time: number;
  duration: number;
  sfx?: string | null;
  sfx_url?: string | null;
  freeze_frame: boolean;
  intensity: number;
}

export interface SpeedRampSegment {
  start: number;
  end: number;
  speed: number;
}

export interface FacecamBox {
  detected: boolean;
  corner: "top_left" | "top_right" | "bottom_left" | "bottom_right";
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ShortClipData {
  clip_id: string;
  index: number;
  title: string;
  hook_banner_text: string;
  viral_score: number;
  viral_reason: string;
  emotion: EmotionTag;
  preset: StylePreset;
  source_start: number;
  source_end: number;
  duration: number;
  fps: number;
  width: number;
  height: number;
  video_url: string;
  audio_mix_url?: string | null;
  bgm_url?: string | null;
  bgm_title: string;
  bpm: number;
  rendered_mp4_url?: string | null;
  render_status: "pending" | "rendering" | "ready" | "failed";
  facecam: FacecamBox;
  captions: WordCaption[];
  annotations: NarrativeAnnotation[];
  beats: BeatMarker[];
  memes: MemeCue[];
  speed_ramps: SpeedRampSegment[];
}

export interface StreamMetadata {
  url: string;
  video_id: string;
  title: string;
  channel: string;
  duration?: number | null;
  is_live: boolean;
  thumbnail?: string | null;
  max_resolution: string;
}

export interface ValidateUrlResponse {
  valid: boolean;
  metadata?: StreamMetadata | null;
  error?: string | null;
}

export interface JobLogEntry {
  timestamp: string;
  stage: string;
  message: string;
  level: "info" | "success" | "warning" | "error";
}

export interface JobState {
  job_id: string;
  url: string;
  num_shorts: number;
  preset: StylePreset;
  status: "queued" | "running" | "completed" | "failed";
  overall_progress: number;
  created_at: string;
  stream_metadata?: StreamMetadata | null;
  stages: PipelineStageState[];
  clips: ShortClipData[];
  zip_download_url?: string | null;
  error?: string | null;
  logs: JobLogEntry[];
}

export interface CreateJobResponse {
  job_id: string;
  ws_url: string;
  status: string;
  job: JobState;
}

export interface BackendHealth {
  status: string;
  service: string;
  ffmpeg_available: boolean;
  yt_dlp_available: boolean;
  gemini_configured: boolean;
  gemini_model: string;
  pixabay_configured: boolean;
  remotion_render_enabled: boolean;
}

export interface PresetOption {
  id: StylePreset;
  name: string;
  tagline: string;
  badge: string;
  accentFrom: string;
  accentTo: string;
  features: string[];
}

export const STYLE_PRESETS: PresetOption[] = [
  {
    id: "strykeditz_phonk",
    name: "Strykeditz Phonk Hype",
    tagline: "Hard bass shakes, exposure flashes, punch-zooms & drift phonk",
    badge: "VIRAL META",
    accentFrom: "#ff2e93",
    accentTo: "#00f0ff",
    features: ["±12px Beat Shake", "1.85x Exposure Flash", "Crushed HDR Phonk"],
  },
  {
    id: "firefly_cinematic",
    name: "Firefly Emotional / Cinematic",
    tagline: "Vice City neon sunset grading, optical slow-mo & italic story beats",
    badge: "8K CINEMA",
    accentFrom: "#ff8a3d",
    accentTo: "#ff2e93",
    features: ["0.45x Optical Slow-Mo", "*Narrative Notes*", "Synthwave Ducking"],
  },
  {
    id: "chaotic_meme",
    name: "Chaotic GTA Meme Edit",
    tagline: "Vine Boom shockwaves, WASTED freeze-frames & rapid neon captions",
    badge: "MAX RETENTION",
    accentFrom: "#ffd43b",
    accentTo: "#ff2e93",
    features: ["GTA Wasted Freeze", "Vine Boom + Bruh SFX", "5-Star Siren Strobes"],
  },
];
