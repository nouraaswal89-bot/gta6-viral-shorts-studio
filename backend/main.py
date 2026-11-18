"""GTA6 Viral Shorts Studio - FastAPI Backend (Fast Two-Phase Pipeline + WebSockets)."""

from __future__ import annotations

import asyncio
import os
import shutil
import time
import uuid
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from assets.sfx.generate_default_assets import ensure_default_assets
from models import (
    BeatMarker,
    CreateJobRequest,
    CreateJobResponse,
    EmotionTag,
    FacecamBox,
    JobLogEntry,
    JobState,
    MemeCue,
    NarrativeAnnotation,
    PipelineStageId,
    PipelineStageState,
    ShortClipData,
    SpeedRampSegment,
    StageStatus,
    StreamMetadata,
    StylePreset,
    ValidateUrlRequest,
    ValidateUrlResponse,
    WordCaption,
)
from pipeline.beat_analyzer import extract_beat_markers
from pipeline.music_fetcher import fetch_copyright_free_bgm
from pipeline.remotion_renderer import render_final_short_mp4
from pipeline.stream_ingestor import (
    IngestResult,
    ingest_local_video,
    ingest_stream,
    validate_youtube_url,
)
from pipeline.video_enhancer import enhance_clip_8k_hdr, generate_demo_vice_city_video_sync
from pipeline.viral_director import direct_viral_clips, transcribe_clip_audio_sync

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")

ASSETS_DIR = BASE_DIR / "assets"
WORKSPACE_DIR = BASE_DIR / "workspace"
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIST_DIR = BASE_DIR.parent / "frontend" / "out"

PUBLIC_BACKEND_URL = os.getenv("PUBLIC_BACKEND_URL", "").rstrip("/")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3001")


def _resolve_public_base_url(request: Request) -> str:
    """Resolve HTTPS public URL dynamically behind Railway proxy or local dev."""
    if PUBLIC_BACKEND_URL:
        return PUBLIC_BACKEND_URL
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost:8000"
    return f"{proto}://{host}".rstrip("/")


def _cleanup_old_jobs_sync(max_age_sec: int = 1800) -> None:
    """Remove workspace job directories older than 30 min to stay lean on Railway $5 trial."""
    now = time.time()
    for child in WORKSPACE_DIR.iterdir():
        if not child.is_dir():
            continue
        try:
            if now - child.stat().st_mtime > max_age_sec:
                shutil.rmtree(child, ignore_errors=True)
        except Exception:
            pass

STAGE_DEFINITIONS: list[tuple[PipelineStageId, int, str]] = [
    (PipelineStageId.INGEST, 1, "Stream Ingest & Peak Scan"),
    (PipelineStageId.AI_DIRECTOR, 2, "AI Clip Select (15–30s)"),
    (PipelineStageId.MUSIC, 3, "Auto Music Match"),
    (PipelineStageId.BEATS_CAPTIONS, 4, "Beat Drops & Captions"),
    (PipelineStageId.ENHANCE_FX, 5, "1080p Clip Fetch, 8K HDR & Ducking"),
    (PipelineStageId.RENDER, 6, "Render 60fps MP4 & ZIP"),
]


class JobRegistry:
    def __init__(self) -> None:
        self.jobs: dict[str, JobState] = {}
        self.sockets: dict[str, set[WebSocket]] = {}

    def create(self, req: CreateJobRequest) -> JobState:
        job_id = uuid.uuid4().hex[:10]
        stages = [
            PipelineStageState(id=sid, index=idx, label=label)
            for sid, idx, label in STAGE_DEFINITIONS
        ]
        job = JobState(
            job_id=job_id,
            url=req.url.strip(),
            num_shorts=req.num_shorts,
            preset=req.preset,
            status="queued",
            stages=stages,
        )
        self.jobs[job_id] = job
        self.sockets[job_id] = set()
        return job

    def get(self, job_id: str) -> JobState:
        job = self.jobs.get(job_id)
        if not job:
            # Recover job state from disk if server restarted / slept on Railway
            state_file = WORKSPACE_DIR / job_id / "job_state.json"
            if state_file.exists():
                job = JobState.model_validate_json(state_file.read_text(encoding="utf-8"))
                self.jobs[job_id] = job
                self.sockets.setdefault(job_id, set())
                return job
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        return job

    async def broadcast(self, job_id: str) -> None:
        job = self.jobs.get(job_id)
        if not job:
            return
        job_dir = WORKSPACE_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "job_state.json").write_text(job.model_dump_json(indent=2), encoding="utf-8")

        payload = job.model_dump(mode="json")
        dead: list[WebSocket] = []
        for ws in list(self.sockets.get(job_id, set())):
            try:
                await ws.send_json({"type": "job_update", "job": payload})
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.sockets.get(job_id, set()).discard(ws)

    async def log(
        self,
        job_id: str,
        stage: str,
        message: str,
        level: str = "info",
    ) -> None:
        job = self.jobs[job_id]
        job.logs.append(
            JobLogEntry(
                timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
                stage=stage,
                message=message,
                level=level,  # type: ignore[arg-type]
            )
        )
        job.logs = job.logs[-60:]
        await self.broadcast(job_id)

    async def update_stage(
        self,
        job_id: str,
        stage_id: PipelineStageId,
        status: StageStatus,
        progress: float,
        detail: str = "",
    ) -> None:
        job = self.jobs[job_id]
        for st in job.stages:
            if st.id == stage_id:
                st.status = status
                st.progress = round(min(100.0, max(0.0, progress)), 1)
                if detail:
                    st.detail = detail
                break
        total = sum(st.progress for st in job.stages)
        job.overall_progress = round(total / max(1, len(job.stages)), 1)
        await self.broadcast(job_id)


registry = JobRegistry()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await asyncio.to_thread(ensure_default_assets)
    yield


app = FastAPI(
    title="GTA6 Viral Shorts Studio API",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")
app.mount("/workspace", StaticFiles(directory=str(WORKSPACE_DIR)), name="workspace")


def _build_zip_archive_sync(job_id: str, mp4_paths: list[Path]) -> Path:
    zip_path = WORKSPACE_DIR / job_id / f"gta6_viral_shorts_{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for p in mp4_paths:
            if p.exists():
                zf.write(p, arcname=p.name)
    return zip_path


async def _run_demo_pipeline(job_id: str, req: CreateJobRequest, base_url: str) -> None:
    """Fast ~5-8s end-to-end GTA 6 showcase pipeline."""
    await asyncio.to_thread(_cleanup_old_jobs_sync)
    job = registry.get(job_id)
    job.status = "running"
    job_dir = WORKSPACE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        await registry.update_stage(job_id, PipelineStageId.INGEST, StageStatus.RUNNING, 35.0, "Generating demo footage...")
        job.stream_metadata = StreamMetadata(
            url=req.url or "https://www.youtube.com/watch?v=QdBZY2fkU-0",
            video_id="QdBZY2fkU-0",
            title="GTA 6 Leonida 5-Star Chase [DEMO]",
            channel="ViceCityLive",
            duration=360.0,
            is_live=False,
            max_resolution="1080p60",
        )
        demo_base = job_dir / "demo_source_9x16.mp4"
        await asyncio.to_thread(generate_demo_vice_city_video_sync, demo_base, 18.0)
        await registry.update_stage(job_id, PipelineStageId.INGEST, StageStatus.COMPLETED, 100.0, "Ready")

        await registry.update_stage(job_id, PipelineStageId.AI_DIRECTOR, StageStatus.RUNNING, 50.0, "Selecting highlights...")
        demo_scripts = [
            {
                "title": "Vice Beach Ramp Jump",
                "hook": "BRO REALLY TRIED THIS IN GTA 6 💀🔥",
                "reason": "5-star ramp jump with instant WASTED drop.",
                "emotion": EmotionTag.HYPE_PHONK,
                "words": [
                    "YO", "WATCH", "THIS", "INSANE", "GTA", "6", "RAMP", "JUMP",
                    "BRO", "NO", "WAY", "THE", "POLICE", "JUST", "SPAWNED",
                    "WAIT", "FOR", "IT", "HE", "IS", "COOKED", "WASTED",
                ],
                "notes": [
                    NarrativeAnnotation(text="*WAIT FOR IT...*", start=2.2, end=5.0, position="upper"),
                    NarrativeAnnotation(text="*INSTANT REGRET*", start=12.2, end=15.8, position="upper"),
                ],
                "memes": [
                    MemeCue(
                        id="demo_m1", type="vine_boom_shockwave", label="VINE BOOM",
                        time=4.0, duration=0.9, sfx="vine_boom.mp3",
                        sfx_url=f"{base_url}/assets/sfx/vine_boom.mp3",
                        freeze_frame=False, intensity=0.95,
                    ),
                    MemeCue(
                        id="demo_m2", type="police_siren_flash", label="5-STAR WANTED",
                        time=8.5, duration=2.0, sfx="whoosh.mp3",
                        sfx_url=f"{base_url}/assets/sfx/whoosh.mp3",
                        freeze_frame=False, intensity=0.92,
                    ),
                    MemeCue(
                        id="demo_m3", type="gta_wasted_overlay", label="WASTED",
                        time=13.2, duration=2.4, sfx="wasted_hit.mp3",
                        sfx_url=f"{base_url}/assets/sfx/wasted_hit.mp3",
                        freeze_frame=True, intensity=1.0,
                    ),
                ],
            },
            {
                "title": "Neon Highway Drift",
                "hook": "5-STAR CHASE AT 220 MPH IN LEONIDA 🚨🏎️",
                "reason": "Clean highway drift between SWAT trucks on bass drop.",
                "emotion": EmotionTag.EPIC_CINEMATIC,
                "words": [
                    "TWO", "HUNDRED", "TWENTY", "MILES", "PER", "HOUR", "IN", "VICE", "CITY",
                    "NO", "BRAKES", "DRIFTING", "PAST", "SWAT", "OH", "MY", "GOD",
                    "SO", "CLEAN", "CLUTCHED", "THE", "ESCAPE",
                ],
                "notes": [
                    NarrativeAnnotation(text="*ZERO BRAKES*", start=2.5, end=5.4, position="upper"),
                    NarrativeAnnotation(text="*THREADED THE NEEDLE*", start=9.8, end=13.2, position="upper"),
                ],
                "memes": [
                    MemeCue(
                        id="demo_m4", type="vine_boom_shockwave", label="WHOA",
                        time=4.8, duration=0.85, sfx="vine_boom.mp3",
                        sfx_url=f"{base_url}/assets/sfx/vine_boom.mp3",
                        freeze_frame=False, intensity=0.9,
                    ),
                    MemeCue(
                        id="demo_m5", type="mission_passed", label="MISSION PASSED +RESPECT",
                        time=13.0, duration=2.5, sfx="whoosh.mp3",
                        sfx_url=f"{base_url}/assets/sfx/whoosh.mp3",
                        freeze_frame=False, intensity=0.95,
                    ),
                ],
            },
            {
                "title": "NPC AI Broke The Lobby",
                "hook": "GTA 6 NPC AI JUST HUMBLED HIM 💀😭",
                "reason": "Unexpected NPC hijack with freeze-frame reaction.",
                "emotion": EmotionTag.FUNNY_MEME,
                "words": [
                    "BRO", "TRIED", "TO", "STEAL", "ONE", "CAR", "AND", "THE", "NPC",
                    "SAID", "NOT", "TODAY", "WAIT", "WHAT", "JUST", "HAPPENED",
                    "BRUH", "DELETE", "THE", "GAME", "INSTANT", "REGRET",
                ],
                "notes": [
                    NarrativeAnnotation(text="*BRO THOUGHT IT WAS EASY*", start=1.8, end=4.8, position="upper"),
                    NarrativeAnnotation(text="*EMOTIONAL DAMAGE*", start=10.2, end=13.8, position="upper"),
                ],
                "memes": [
                    MemeCue(
                        id="demo_m6", type="zoom_freeze_frame", label="RECORD SCRATCH",
                        time=9.4, duration=1.5, sfx="bruh.mp3",
                        sfx_url=f"{base_url}/assets/sfx/bruh.mp3",
                        freeze_frame=True, intensity=0.95,
                    ),
                    MemeCue(
                        id="demo_m7", type="skull_reaction", label="COOKED 💀",
                        time=13.4, duration=1.6, sfx="vine_boom.mp3",
                        sfx_url=f"{base_url}/assets/sfx/vine_boom.mp3",
                        freeze_frame=False, intensity=0.9,
                    ),
                ],
            },
        ]
        await registry.update_stage(job_id, PipelineStageId.AI_DIRECTOR, StageStatus.COMPLETED, 100.0, f"{req.num_shorts} clips")

        await registry.update_stage(job_id, PipelineStageId.MUSIC, StageStatus.RUNNING, 40.0, "Matching BGM...")
        bgm_by_emotion = {}
        for idx in range(req.num_shorts):
            sc = demo_scripts[idx % len(demo_scripts)]
            emo = (
                EmotionTag.EPIC_CINEMATIC if req.preset == StylePreset.FIREFLY_CINEMATIC
                else EmotionTag.FUNNY_MEME if req.preset == StylePreset.CHAOTIC_MEME
                else sc["emotion"]
            )
            if emo not in bgm_by_emotion:
                bgm_by_emotion[emo] = await fetch_copyright_free_bgm(emo, job_dir, base_url)
        await registry.update_stage(job_id, PipelineStageId.MUSIC, StageStatus.COMPLETED, 100.0, "BGM Ready")

        await registry.update_stage(job_id, PipelineStageId.BEATS_CAPTIONS, StageStatus.RUNNING, 40.0, "Analyzing beats...")
        clip_duration = 18.0
        beats_cache: dict[EmotionTag, tuple[float, list[BeatMarker]]] = {}
        for emo, track in bgm_by_emotion.items():
            beats_cache[emo] = await extract_beat_markers(Path(track.local_path), clip_duration)
        await registry.update_stage(job_id, PipelineStageId.BEATS_CAPTIONS, StageStatus.COMPLETED, 100.0, "Beats locked")

        await registry.update_stage(job_id, PipelineStageId.ENHANCE_FX, StageStatus.RUNNING, 25.0, "Enhancing & mixing...")
        final_mp4s: list[Path] = []

        async def _build_demo_clip(idx: int) -> tuple[ShortClipData, Path]:
            sc = demo_scripts[idx % len(demo_scripts)]
            emo = (
                EmotionTag.EPIC_CINEMATIC if req.preset == StylePreset.FIREFLY_CINEMATIC
                else EmotionTag.FUNNY_MEME if req.preset == StylePreset.CHAOTIC_MEME
                else sc["emotion"]
            )
            track = bgm_by_emotion[emo]
            bpm, beats = beats_cache[emo]
            clip_id = f"clip_{idx + 1:02d}_{uuid.uuid4().hex[:6]}"
            clip_dir = job_dir / clip_id

            words_list: list[str] = sc["words"]
            step = (clip_duration - 1.2) / max(1, len(words_list))
            captions = [
                WordCaption(
                    word=w_txt,
                    start=round(0.45 + w_i * step, 3),
                    end=round(0.45 + w_i * step + step * 0.92, 3),
                    emphasis=(w_i % 3 == 0),
                    color="red" if w_txt in ("WASTED", "COOKED", "POLICE", "INSANE", "REGRET") else (
                        "cyan" if w_txt in ("GTA", "6", "VICE", "CITY", "DRIFTING", "CLUTCHED", "SWAT") else "yellow"
                    ),  # type: ignore[arg-type]
                )
                for w_i, w_txt in enumerate(words_list)
            ]

            enhanced_video, audio_mix = await enhance_clip_8k_hdr(
                source_video=demo_base,
                bgm_path=Path(track.local_path),
                clip_dir=clip_dir,
                start_sec=0.0,
                duration=clip_duration,
                preset=req.preset,
                beats=beats,
                memes=sc["memes"],
                speed_ramps=[],
            )
            clip_data = ShortClipData(
                clip_id=clip_id,
                index=idx + 1,
                title=sc["title"] if idx < len(demo_scripts) else f"{sc['title']} #{idx + 1}",
                hook_banner_text=sc["hook"],
                viral_score=max(85, 98 - idx * 2),
                viral_reason=sc["reason"],
                emotion=emo,
                preset=req.preset,
                source_start=float(idx * 25),
                source_end=float(idx * 25 + clip_duration),
                duration=clip_duration,
                fps=int(os.getenv("OUTPUT_FPS", "30")),
                width=1080,
                height=1920,
                video_url=f"{base_url}/workspace/{job_id}/{clip_id}/{enhanced_video.name}",
                audio_mix_url=f"{base_url}/workspace/{job_id}/{clip_id}/{audio_mix.name}",
                bgm_url=track.url,
                bgm_title=track.title,
                bpm=bpm,
                render_status="rendering",
                facecam=FacecamBox(detected=False, corner="top_right"),
                captions=captions,
                annotations=sc["notes"],
                beats=beats,
                memes=sc["memes"],
                speed_ramps=[SpeedRampSegment(start=12.6, end=14.4, speed=0.45)],
            )
            return clip_data, enhanced_video

        results = await asyncio.gather(*[_build_demo_clip(i) for i in range(req.num_shorts)])
        await registry.update_stage(job_id, PipelineStageId.ENHANCE_FX, StageStatus.COMPLETED, 100.0, "Enhanced")

        await registry.update_stage(job_id, PipelineStageId.RENDER, StageStatus.RUNNING, 30.0, "Exporting MP4s...")
        for clip_data, enhanced_video in results:
            clip_dir = job_dir / clip_data.clip_id
            out_mp4, _engine = await render_final_short_mp4(clip_data, enhanced_video, clip_dir)
            clip_data.rendered_mp4_url = f"{base_url}/api/jobs/{job_id}/clips/{clip_data.clip_id}/download"
            clip_data.render_status = "ready"
            job.clips.append(clip_data)
            final_mp4s.append(out_mp4)

        await asyncio.to_thread(_build_zip_archive_sync, job_id, final_mp4s)
        job.zip_download_url = f"{base_url}/api/jobs/{job_id}/download-all"
        job.status = "completed"
        await registry.update_stage(job_id, PipelineStageId.RENDER, StageStatus.COMPLETED, 100.0, "Done")
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        await registry.log(job_id, "error", str(exc), level="error")


async def _run_pipeline_from_ingest(
    job_id: str,
    req: CreateJobRequest,
    base_url: str,
    local_upload_path: Path | None = None,
    local_title: str = "Uploaded Gameplay",
) -> None:
    """Fast unified pipeline for both YouTube URLs (single-pass yt-dlp) and local video uploads."""
    await asyncio.to_thread(_cleanup_old_jobs_sync)
    job = registry.get(job_id)
    job.status = "running"
    job_dir = WORKSPACE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        # STAGE 1: Lightweight Audio Ingest + Instant RMS Peak Scan (~3-6s)
        await registry.update_stage(job_id, PipelineStageId.INGEST, StageStatus.RUNNING, 10.0, "Scanning stream...")

        async def _ingest_cb(pct: float, msg: str) -> None:
            await registry.update_stage(job_id, PipelineStageId.INGEST, StageStatus.RUNNING, pct, msg)
            await registry.log(job_id, "ingest", msg)

        if local_upload_path is not None:
            ingest_res = await ingest_local_video(
                local_upload_path, job_dir / "source", local_title, progress_cb=_ingest_cb
            )
        else:
            ingest_res = await ingest_stream(
                req.url, job_dir / "source", num_shorts=req.num_shorts, progress_cb=_ingest_cb
            )
        job.stream_metadata = ingest_res.metadata
        await registry.update_stage(job_id, PipelineStageId.INGEST, StageStatus.COMPLETED, 100.0, f"{len(ingest_res.peaks)} peaks")

        # STAGE 2: AI Creative Director (~2-3s)
        await registry.update_stage(job_id, PipelineStageId.AI_DIRECTOR, StageStatus.RUNNING, 20.0, "Picking clips...")

        async def _dir_cb(pct: float, msg: str) -> None:
            await registry.update_stage(job_id, PipelineStageId.AI_DIRECTOR, StageStatus.RUNNING, pct, msg)
            await registry.log(job_id, "ai_director", msg)

        blueprints = await direct_viral_clips(
            peaks=ingest_res.peaks,
            video_duration=ingest_res.duration,
            num_shorts=req.num_shorts,
            preset=req.preset,
            stream_title=ingest_res.metadata.title,
            public_base_url=base_url,
            progress_cb=_dir_cb,
        )
        await registry.update_stage(job_id, PipelineStageId.AI_DIRECTOR, StageStatus.COMPLETED, 100.0, f"{len(blueprints)} clips")

        # STAGE 3: Auto-Match Copyright-Free BGM (~0.5-2s)
        await registry.update_stage(job_id, PipelineStageId.MUSIC, StageStatus.RUNNING, 25.0, "Matching music...")
        unique_emotions = list({bp["emotion"] for bp in blueprints})
        bgm_tracks = await asyncio.gather(
            *[fetch_copyright_free_bgm(emo, job_dir, base_url) for emo in unique_emotions]
        )
        bgm_map = dict(zip(unique_emotions, bgm_tracks))
        await registry.update_stage(job_id, PipelineStageId.MUSIC, StageStatus.COMPLETED, 100.0, f"{len(bgm_map)} track(s)")

        # STAGE 4: Beat Extraction (librosa) + Per-Clip Word Captions (Cached Faster-Whisper tiny) (~2-5s)
        await registry.update_stage(job_id, PipelineStageId.BEATS_CAPTIONS, StageStatus.RUNNING, 20.0, "Beats & captions...")
        beats_by_emo: dict[EmotionTag, tuple[float, list[BeatMarker]]] = {}
        for emo, track in bgm_map.items():
            beats_by_emo[emo] = await extract_beat_markers(Path(track.local_path), 30.0)

        clip_captions: list[list[WordCaption]] = []
        for idx, bp in enumerate(blueprints):
            caps = await asyncio.to_thread(
                transcribe_clip_audio_sync, ingest_res.audio_path, bp["start_sec"], bp["duration"]
            )
            clip_captions.append(caps)
            await registry.update_stage(
                job_id, PipelineStageId.BEATS_CAPTIONS, StageStatus.RUNNING,
                ((idx + 1) / len(blueprints)) * 100.0,
                f"Clip {idx + 1}/{len(blueprints)}",
            )
        await registry.update_stage(job_id, PipelineStageId.BEATS_CAPTIONS, StageStatus.COMPLETED, 100.0, "Done")

        # STAGE 5: Local FFmpeg 8K CAS/HDR + Sidechain Audio Ducking (~4-8s per clip, parallel!)
        await registry.update_stage(job_id, PipelineStageId.ENHANCE_FX, StageStatus.RUNNING, 15.0, "Grading...")
        sem = asyncio.Semaphore(2)
        completed_count = 0

        async def _process_one_clip(idx: int, bp: dict) -> tuple[ShortClipData, Path]:
            nonlocal completed_count
            async with sem:
                clip_id = f"clip_{idx + 1:02d}_{uuid.uuid4().hex[:6]}"
                clip_dir = job_dir / clip_id
                clip_dir.mkdir(parents=True, exist_ok=True)
                track = bgm_map[bp["emotion"]]
                bpm, all_beats = beats_by_emo[bp["emotion"]]
                beats = [b for b in all_beats if b.time <= bp["duration"] - 0.15]
                captions = clip_captions[idx]

                enhanced_video, audio_mix = await enhance_clip_8k_hdr(
                    source_video=ingest_res.video_path,
                    bgm_path=Path(track.local_path),
                    clip_dir=clip_dir,
                    start_sec=bp["start_sec"],
                    duration=bp["duration"],
                    preset=req.preset,
                    beats=beats,
                    memes=bp["memes"],
                    speed_ramps=bp["speed_ramps"],
                )

                completed_count += 1
                await registry.update_stage(
                    job_id, PipelineStageId.ENHANCE_FX, StageStatus.RUNNING,
                    (completed_count / len(blueprints)) * 100.0,
                    f"Graded {completed_count}/{len(blueprints)}",
                )

                facecam = ingest_res.facecam if req.enable_facecam_pip else FacecamBox(detected=False)
                clip_data = ShortClipData(
                    clip_id=clip_id,
                    index=idx + 1,
                    title=bp["title"],
                    hook_banner_text=bp["hook_banner_text"],
                    viral_score=bp["viral_score"],
                    viral_reason=bp["viral_reason"],
                    emotion=bp["emotion"],
                    preset=req.preset,
                    source_start=bp["start_sec"],
                    source_end=bp["end_sec"],
                    duration=bp["duration"],
                    fps=int(os.getenv("OUTPUT_FPS", "30")),
                    width=1080,
                    height=1920,
                    video_url=f"{base_url}/workspace/{job_id}/{clip_id}/{enhanced_video.name}",
                    audio_mix_url=f"{base_url}/workspace/{job_id}/{clip_id}/{audio_mix.name}",
                    bgm_url=track.url,
                    bgm_title=track.title,
                    bpm=bpm,
                    render_status="rendering",
                    facecam=facecam,
                    captions=captions,
                    annotations=bp["annotations"],
                    beats=beats,
                    memes=bp["memes"],
                    speed_ramps=bp["speed_ramps"],
                )
                return clip_data, enhanced_video

        processed = await asyncio.gather(*[_process_one_clip(i, bp) for i, bp in enumerate(blueprints)])
        processed.sort(key=lambda pair: pair[0].index)
        await registry.update_stage(job_id, PipelineStageId.ENHANCE_FX, StageStatus.COMPLETED, 100.0, "Graded")

        # STAGE 6: Fast 60fps MP4 Export + Batch ZIP (~2-4s per clip)
        await registry.update_stage(job_id, PipelineStageId.RENDER, StageStatus.RUNNING, 15.0, "Exporting MP4s...")
        final_mp4s: list[Path] = []
        for idx, (clip_data, enhanced_video) in enumerate(processed):
            clip_dir = job_dir / clip_data.clip_id
            out_mp4, engine = await render_final_short_mp4(clip_data, enhanced_video, clip_dir)
            clip_data.rendered_mp4_url = f"{base_url}/api/jobs/{job_id}/clips/{clip_data.clip_id}/download"
            clip_data.render_status = "ready"
            job.clips.append(clip_data)
            final_mp4s.append(out_mp4)
            await registry.log(job_id, "render", f"Short #{clip_data.index} ready ({engine})", level="success")
            await registry.update_stage(
                job_id, PipelineStageId.RENDER, StageStatus.RUNNING,
                ((idx + 1) / len(processed)) * 95.0,
                f"Exported {idx + 1}/{len(processed)}",
            )

        await asyncio.to_thread(_build_zip_archive_sync, job_id, final_mp4s)
        job.zip_download_url = f"{base_url}/api/jobs/{job_id}/download-all"
        job.status = "completed"
        await registry.update_stage(job_id, PipelineStageId.RENDER, StageStatus.COMPLETED, 100.0, "Ready")
        await registry.log(job_id, "render", "Complete!", level="success")

    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        for st in job.stages:
            if st.status == StageStatus.RUNNING:
                st.status = StageStatus.FAILED
                st.detail = str(exc)
        await registry.log(job_id, "error", str(exc), level="error")
        await registry.broadcast(job_id)


@app.get("/api/health")
async def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "GTA6 Viral Shorts Studio",
        "ffmpeg_available": bool(shutil.which("ffmpeg")),
        "yt_dlp_available": bool(shutil.which("yt-dlp")),
        "gemini_configured": bool(
            os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_API_KEY") != "your_gemini_api_key_here"
        ),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-4-hydrogen"),
        "pixabay_configured": bool(os.getenv("PIXABAY_API_KEY")),
        "remotion_render_enabled": os.getenv("ENABLE_REMOTION_RENDER", "false").lower() == "true",
    }


@app.post("/api/validate-url", response_model=ValidateUrlResponse)
async def api_validate_url(req: ValidateUrlRequest) -> ValidateUrlResponse:
    try:
        metadata = await validate_youtube_url(req.url)
        return ValidateUrlResponse(valid=True, metadata=metadata)
    except Exception as exc:
        return ValidateUrlResponse(valid=False, error=str(exc))


@app.post("/api/jobs", response_model=CreateJobResponse)
async def api_create_job(req: CreateJobRequest, request: Request) -> CreateJobResponse:
    base_url = _resolve_public_base_url(request)
    job = registry.create(req)
    if req.demo_mode:
        asyncio.create_task(_run_demo_pipeline(job.job_id, req, base_url))
    else:
        asyncio.create_task(_run_pipeline_from_ingest(job.job_id, req, base_url))

    ws_base = base_url.replace("https://", "wss://").replace("http://", "ws://")
    return CreateJobResponse(
        job_id=job.job_id,
        ws_url=f"{ws_base}/ws/jobs/{job.job_id}",
        status=job.status,
        job=job,
    )


@app.post("/api/jobs/upload", response_model=CreateJobResponse)
async def api_upload_video_job(
    request: Request,
    file: UploadFile = File(...),
    num_shorts: int = Form(default=3),
    preset: StylePreset = Form(default=StylePreset.STRYKEDITZ_PHONK),
    enable_facecam_pip: bool = Form(default=True),
) -> CreateJobResponse:
    """Instant local video upload endpoint (zero YouTube download delay)."""
    base_url = _resolve_public_base_url(request)
    req = CreateJobRequest(
        url=f"local://{file.filename or 'gameplay.mp4'}",
        num_shorts=max(1, min(20, num_shorts)),
        preset=preset,
        enable_facecam_pip=enable_facecam_pip,
        demo_mode=False,
    )
    job = registry.create(req)
    upload_dir = WORKSPACE_DIR / job.job_id / "upload"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "gameplay.mp4").name
    dest = upload_dir / safe_name

    with dest.open("wb") as out_f:
        shutil.copyfileobj(file.file, out_f)

    asyncio.create_task(
        _run_pipeline_from_ingest(
            job.job_id, req, base_url, local_upload_path=dest, local_title=Path(safe_name).stem
        )
    )
    ws_base = base_url.replace("https://", "wss://").replace("http://", "ws://")
    return CreateJobResponse(
        job_id=job.job_id,
        ws_url=f"{ws_base}/ws/jobs/{job.job_id}",
        status=job.status,
        job=job,
    )


@app.get("/api/jobs/{job_id}", response_model=JobState)
async def api_get_job(job_id: str) -> JobState:
    return registry.get(job_id)


@app.get("/api/jobs/{job_id}/clips/{clip_id}/download")
async def api_download_clip(job_id: str, clip_id: str) -> FileResponse:
    job = registry.get(job_id)
    clip = next((c for c in job.clips if c.clip_id == clip_id), None)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")

    clip_dir = WORKSPACE_DIR / job_id / clip_id
    mp4_candidates = sorted(clip_dir.glob("gta6_short_*.mp4"))
    target = mp4_candidates[0] if mp4_candidates else clip_dir / "enhanced_9x16_hdr.mp4"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Rendered MP4 not found.")

    return FileResponse(
        path=str(target),
        media_type="video/mp4",
        filename=f"GTA6_Viral_Short_{clip.index:02d}.mp4",
    )


@app.get("/api/jobs/{job_id}/download-all")
async def api_download_all_zip(job_id: str) -> FileResponse:
    _ = registry.get(job_id)
    zip_path = WORKSPACE_DIR / job_id / f"gta6_viral_shorts_{job_id}.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Batch ZIP not ready.")
    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"GTA6_Viral_Shorts_Batch_{job_id}.zip",
    )


@app.websocket("/ws/jobs/{job_id}")
async def ws_job_progress(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    if job_id not in registry.jobs:
        await websocket.send_json({"type": "error", "message": f"Job '{job_id}' not found."})
        await websocket.close(code=4404)
        return

    registry.sockets.setdefault(job_id, set()).add(websocket)
    try:
        await websocket.send_json({
            "type": "job_update",
            "job": registry.jobs[job_id].model_dump(mode="json"),
        })
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        registry.sockets.get(job_id, set()).discard(websocket)


# Serve static Next.js build at root "/" for unified single-container Railway deployment
if FRONTEND_DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")

