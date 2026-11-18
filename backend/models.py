"""Pydantic schemas shared across the GTA6 Viral Shorts Studio pipeline and API."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class StylePreset(str, Enum):
    STRYKEDITZ_PHONK = "strykeditz_phonk"
    FIREFLY_CINEMATIC = "firefly_cinematic"
    CHAOTIC_MEME = "chaotic_meme"


class EmotionTag(str, Enum):
    HYPE_PHONK = "hype_phonk"
    FUNNY_MEME = "funny_meme"
    EPIC_CINEMATIC = "epic_cinematic"


class PipelineStageId(str, Enum):
    INGEST = "ingest"
    AI_DIRECTOR = "ai_director"
    MUSIC = "music"
    BEATS_CAPTIONS = "beats_captions"
    ENHANCE_FX = "enhance_fx"
    RENDER = "render"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStageState(BaseModel):
    id: PipelineStageId
    index: int
    label: str
    status: StageStatus = StageStatus.PENDING
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    detail: str = ""


class WordCaption(BaseModel):
    word: str
    start: float = Field(ge=0.0, description="Start time in seconds relative to clip start")
    end: float = Field(ge=0.0, description="End time in seconds relative to clip start")
    emphasis: bool = False
    color: Literal["yellow", "cyan", "red", "white"] = "yellow"


class NarrativeAnnotation(BaseModel):
    text: str = Field(description="Firefly-style annotation, e.g. *INSTANT REGRET*")
    start: float = Field(ge=0.0)
    end: float = Field(ge=0.0)
    position: Literal["upper", "middle", "lower"] = "upper"


class BeatMarker(BaseModel):
    time: float = Field(ge=0.0, description="Beat timestamp in seconds relative to clip start")
    strength: float = Field(ge=0.0, le=1.0, description="Normalized onset/bass intensity")
    is_drop: bool = Field(default=False, description="True for heavy bass drops triggering camera shake + flash")


class MemeCue(BaseModel):
    id: str
    type: Literal[
        "gta_wasted_overlay",
        "vine_boom_shockwave",
        "zoom_freeze_frame",
        "skull_reaction",
        "police_siren_flash",
        "mission_passed",
    ]
    label: str
    time: float = Field(ge=0.0, description="Trigger timestamp in seconds relative to clip start")
    duration: float = Field(default=1.4, ge=0.3, le=5.0)
    sfx: Optional[str] = None
    sfx_url: Optional[str] = None
    freeze_frame: bool = False
    intensity: float = Field(default=0.85, ge=0.1, le=1.0)


class SpeedRampSegment(BaseModel):
    start: float = Field(ge=0.0)
    end: float = Field(ge=0.0)
    speed: float = Field(default=0.45, ge=0.25, le=2.0)


class FacecamBox(BaseModel):
    detected: bool = False
    corner: Literal["top_left", "top_right", "bottom_left", "bottom_right"] = "top_right"
    x: float = 0.72
    y: float = 0.04
    width: float = 0.25
    height: float = 0.24


class MusicTrackInfo(BaseModel):
    title: str
    artist: str = "Royalty-Free Audio"
    source: Literal["pixabay", "yt_dlp_ncs", "local_library", "synth_fallback"] = "local_library"
    emotion: EmotionTag
    bpm: float = 128.0
    local_path: str
    url: str


class ShortClipData(BaseModel):
    clip_id: str
    index: int
    title: str
    hook_banner_text: str = Field(description="Top white bar curiosity hook text")
    viral_score: int = Field(ge=1, le=100)
    viral_reason: str
    emotion: EmotionTag
    preset: StylePreset
    source_start: float
    source_end: float
    duration: float = Field(ge=5.0, le=30.0)
    fps: int = 30
    width: int = 1080
    height: int = 1920
    video_url: str
    audio_mix_url: Optional[str] = None
    bgm_url: Optional[str] = None
    bgm_title: str = "Vice City Phonk"
    bpm: float = 128.0
    rendered_mp4_url: Optional[str] = None
    render_status: Literal["pending", "rendering", "ready", "failed"] = "pending"
    facecam: FacecamBox = Field(default_factory=FacecamBox)
    captions: list[WordCaption] = Field(default_factory=list)
    annotations: list[NarrativeAnnotation] = Field(default_factory=list)
    beats: list[BeatMarker] = Field(default_factory=list)
    memes: list[MemeCue] = Field(default_factory=list)
    speed_ramps: list[SpeedRampSegment] = Field(default_factory=list)


class StreamMetadata(BaseModel):
    url: str
    video_id: str
    title: str
    channel: str = "Unknown Channel"
    duration: Optional[float] = None
    is_live: bool = False
    thumbnail: Optional[str] = None
    max_resolution: str = "1080p60"


class ValidateUrlRequest(BaseModel):
    url: str


class ValidateUrlResponse(BaseModel):
    valid: bool
    metadata: Optional[StreamMetadata] = None
    error: Optional[str] = None


class CreateJobRequest(BaseModel):
    url: str
    num_shorts: int = Field(default=3, ge=1, le=20)
    preset: StylePreset = StylePreset.STRYKEDITZ_PHONK
    enable_facecam_pip: bool = True
    demo_mode: bool = False


class JobLogEntry(BaseModel):
    timestamp: str
    stage: str
    message: str
    level: Literal["info", "success", "warning", "error"] = "info"


class JobState(BaseModel):
    job_id: str
    url: str
    num_shorts: int
    preset: StylePreset
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    overall_progress: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stream_metadata: Optional[StreamMetadata] = None
    stages: list[PipelineStageState] = Field(default_factory=list)
    clips: list[ShortClipData] = Field(default_factory=list)
    zip_download_url: Optional[str] = None
    error: Optional[str] = None
    logs: list[JobLogEntry] = Field(default_factory=list)


class CreateJobResponse(BaseModel):
    job_id: str
    ws_url: str
    status: str
    job: JobState


# --- Structured output models for Google Gemini AI Creative Director ---

class GeminiMemeSuggestion(BaseModel):
    type: Literal[
        "gta_wasted_overlay",
        "vine_boom_shockwave",
        "zoom_freeze_frame",
        "skull_reaction",
        "police_siren_flash",
        "mission_passed",
    ]
    label: str
    relative_time: float = Field(description="Seconds after clip start (0 to clip duration)")
    duration: float = Field(default=1.4)
    freeze_frame: bool = False


class GeminiAnnotationSuggestion(BaseModel):
    text: str = Field(description="Short uppercase italic narrative annotation wrapped in asterisks, e.g. *INSTANT REGRET*")
    relative_start: float
    relative_end: float
    position: Literal["upper", "middle", "lower"] = "upper"


class GeminiSpeedRampSuggestion(BaseModel):
    relative_start: float
    relative_end: float
    speed: float = Field(default=0.45)


class GeminiSelectedClip(BaseModel):
    start_sec: float = Field(description="Exact clip start timestamp in seconds within the source video")
    end_sec: float = Field(description="Exact clip end timestamp in seconds; MUST be strictly 15 to 30 seconds after start_sec")
    title: str = Field(description="Short punchy internal clip title")
    hook_banner_text: str = Field(description="ALL-CAPS Gen-Z curiosity hook with 1-2 emojis for the top white banner, max 52 chars")
    viral_score: int = Field(ge=60, le=100)
    viral_reason: str
    emotion: Literal["hype_phonk", "funny_meme", "epic_cinematic"]
    annotations: list[GeminiAnnotationSuggestion]
    memes: list[GeminiMemeSuggestion]
    speed_ramps: list[GeminiSpeedRampSuggestion] = Field(default_factory=list)


class GeminiDirectorOutput(BaseModel):
    clips: list[GeminiSelectedClip]
    metadata_notes: Optional[str] = None
