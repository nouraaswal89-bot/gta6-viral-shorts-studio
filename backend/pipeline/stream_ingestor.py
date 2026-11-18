"""Fast Two-Phase YouTube Livestream & VOD Ingestor.

Phase 1 (2-5s): Download lightweight audio-only stream & detect loudness peaks in <0.1s.
Phase 2 (3-6s/clip): Download ONLY the selected 15-30s clip segments in crisp 1080p60.
Avoids downloading gigabytes of unused 4K footage or doing hundreds of slow OpenCV seeks.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Optional

import cv2
import numpy as np

from models import FacecamBox, StreamMetadata

YOUTUBE_URL_REGEX = re.compile(
    r"^(https?://)?(www\.|m\.)?"
    r"(youtube\.com/(watch\?v=|live/|shorts/|embed/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)

ProgressCallback = Optional[Callable[[float, str], Awaitable[None]]]


@dataclass
class EnergyPeak:
    time_sec: float
    audio_score: float
    motion_score: float
    combined_score: float


@dataclass
class IngestResult:
    metadata: StreamMetadata
    url: str
    audio_path: Path
    duration: float
    window_offset: float
    peaks: list[EnergyPeak]
    video_path: Optional[Path] = None


def extract_youtube_id(url: str) -> Optional[str]:
    match = YOUTUBE_URL_REGEX.search(url.strip())
    if match:
        return match.group(5)
    m = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def _get_yt_dlp_bin() -> str:
    return shutil.which("yt-dlp") or "yt-dlp"


def _get_ffmpeg_bin() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def _get_ffprobe_bin() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def probe_media_duration(media_path: Path) -> float:
    """Return accurate duration in seconds via ffprobe."""
    cmd = [
        _get_ffprobe_bin(),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        return max(0.0, float(out))
    except Exception:
        return 0.0


async def validate_youtube_url(url: str) -> StreamMetadata:
    """Validate URL and fetch stream/VOD metadata via yt-dlp without downloading."""
    video_id = extract_youtube_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL.")

    def _fetch_info() -> dict:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    info = await asyncio.to_thread(_fetch_info)
    if not info:
        raise ValueError("Unable to read YouTube metadata.")

    formats = info.get("formats") or []
    has_60 = any((f.get("fps") or 0) >= 50 for f in formats)
    res_label = "1080p60" if has_60 else "1080p"

    return StreamMetadata(
        url=url.strip(),
        video_id=info.get("id") or video_id,
        title=info.get("title") or "GTA 6 Gameplay",
        channel=info.get("uploader") or info.get("channel") or "YouTube",
        duration=float(info["duration"]) if info.get("duration") else None,
        is_live=bool(info.get("is_live", False)),
        thumbnail=info.get("thumbnail"),
        max_resolution=res_label,
    )


async def download_fast_audio(
    url: str,
    metadata: StreamMetadata,
    output_dir: Path,
    progress_cb: ProgressCallback = None,
) -> tuple[Path, float, float]:
    """Download lightweight audio-only stream (few MB, takes ~2-5s) and convert to 16kHz WAV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_wav = output_dir / "source_audio.wav"
    live_buffer_sec = int(os.getenv("LIVE_BUFFER_SECONDS", "90"))
    max_scan_sec = int(os.getenv("MAX_SCAN_SECONDS", "240"))

    window_offset = 0.0
    if not metadata.is_live and metadata.duration and metadata.duration > max_scan_sec:
        window_offset = min(30.0, round(metadata.duration * 0.05, 1))

    if progress_cb:
        await progress_cb(22.0, "Fetching lightweight audio track via yt-dlp...")

    def _run_audio_dl() -> Path:
        yt_dlp_bin = _get_yt_dlp_bin()
        out_tmpl = str(output_dir / "audio_raw.%(ext)s")

        cmd = [
            yt_dlp_bin,
            "--no-playlist",
            "--no-warnings",
            "--concurrent-fragments",
            "8",
            "-f",
            "bestaudio[ext=m4a]/bestaudio/best",
            "-o",
            out_tmpl,
        ]

        if metadata.is_live:
            cmd.extend(["--live-from-start", "--download-sections", f"*0-{live_buffer_sec}"])
        elif metadata.duration and metadata.duration > max_scan_sec:
            end_s = min(int(metadata.duration), int(window_offset + max_scan_sec))
            cmd.extend(["--download-sections", f"*{int(window_offset)}-{end_s}"])

        cmd.append(url)
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            # Fallback without --download-sections
            fallback_cmd = [
                yt_dlp_bin,
                "--no-playlist",
                "--no-warnings",
                "--concurrent-fragments",
                "8",
                "-f",
                "bestaudio[ext=m4a]/bestaudio/best",
                "-o",
                out_tmpl,
                url,
            ]
            res2 = subprocess.run(fallback_cmd, capture_output=True, text=True)
            if res2.returncode != 0:
                raise RuntimeError(f"yt-dlp audio fetch failed: {(res2.stderr or res.stderr)[:300]}")

        files = sorted(output_dir.glob("audio_raw.*"))
        if not files:
            raise FileNotFoundError("No audio downloaded.")
        raw_audio = files[0]

        # Fast 16kHz mono PCM conversion (capped to max_scan_sec for speed)
        subprocess.run(
            [
                _get_ffmpeg_bin(),
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(raw_audio),
                "-t",
                str(max_scan_sec),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(audio_wav),
            ],
            check=True,
        )
        raw_audio.unlink(missing_ok=True)
        return audio_wav

    await asyncio.to_thread(_run_audio_dl)
    dur = await asyncio.to_thread(probe_media_duration, audio_wav)
    return audio_wav, dur, window_offset


def detect_audio_energy_peaks(audio_path: Path, top_k: int = 12) -> list[EnergyPeak]:
    """Ultra-fast (<50ms) NumPy RMS + transient peak detection on 16kHz audio."""
    with wave.open(str(audio_path), "rb") as wf:
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    total_sec = max(1, int(len(samples) / sr))

    # Vectorized 1-second RMS and peak amplitude
    trimmed = samples[: total_sec * sr].reshape(total_sec, sr)
    rms = np.sqrt(np.mean(trimmed ** 2, axis=1))
    peak_amp = np.max(np.abs(trimmed), axis=1)

    if rms.max() > 0:
        rms = rms / rms.max()
    if peak_amp.max() > 0:
        peak_amp = peak_amp / peak_amp.max()

    # Excitement = sustained loudness + sudden shout/explosion transients
    combined = 0.65 * rms + 0.35 * peak_amp
    order = np.argsort(combined)[::-1]

    peaks: list[EnergyPeak] = []
    chosen: list[int] = []
    for idx in order:
        sec = int(idx)
        if any(abs(sec - c) < 16 for c in chosen):
            continue
        chosen.append(sec)
        peaks.append(
            EnergyPeak(
                time_sec=float(sec),
                audio_score=round(float(rms[sec]), 3),
                motion_score=round(float(peak_amp[sec]), 3),
                combined_score=round(float(combined[sec]), 3),
            )
        )
        if len(peaks) >= top_k:
            break

    peaks.sort(key=lambda p: p.combined_score, reverse=True)
    return peaks


def detect_facecam_fast(video_path: Path) -> FacecamBox:
    """Fast facecam check on 4 sampled frames (<150ms), resilient across OpenCV 4.x and 5.x."""
    try:
        classifier_cls = getattr(cv2, "CascadeClassifier", None)
        data_mod = getattr(cv2, "data", None)
        if classifier_cls is None or data_mod is None or not hasattr(data_mod, "haarcascades"):
            return FacecamBox(detected=False)

        cascade_path = data_mod.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = classifier_cls(cascade_path)
        if face_cascade.empty():
            return FacecamBox(detected=False)

        cap = cv2.VideoCapture(str(video_path))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total <= 0:
            cap.release()
            return FacecamBox(detected=False)

        votes = {"top_left": 0, "top_right": 0, "bottom_left": 0, "bottom_right": 0}
        for idx in np.linspace(0, max(0, total - 1), num=4, dtype=int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            small = cv2.resize(frame, (480, 270))
            h, w = small.shape[:2]
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.2, 4, minSize=(22, 22))
            for (fx, fy, fw, fh) in faces:
                cx, cy = (fx + fw / 2) / w, (fy + fh / 2) / h
                if cx < 0.35 and cy < 0.38:
                    votes["top_left"] += 1
                elif cx > 0.65 and cy < 0.38:
                    votes["top_right"] += 1
                elif cx < 0.35 and cy > 0.62:
                    votes["bottom_left"] += 1
                elif cx > 0.65 and cy > 0.62:
                    votes["bottom_right"] += 1
        cap.release()

        best_corner, count = max(votes.items(), key=lambda kv: kv[1])
        if count < 2:
            return FacecamBox(detected=False)

        coords = {
            "top_left": (0.02, 0.03, 0.24, 0.24),
            "top_right": (0.74, 0.03, 0.24, 0.24),
            "bottom_left": (0.02, 0.72, 0.24, 0.24),
            "bottom_right": (0.74, 0.72, 0.24, 0.24),
        }[best_corner]

        return FacecamBox(
            detected=True,
            corner=best_corner,  # type: ignore[arg-type]
            x=coords[0],
            y=coords[1],
            width=coords[2],
            height=coords[3],
        )
    except Exception:
        return FacecamBox(detected=False)


async def ingest_stream(
    url: str,
    output_dir: Path,
    progress_cb: ProgressCallback = None,
) -> IngestResult:
    """Fast Stage 1: resolve metadata, download lightweight audio, detect energy peaks in seconds."""
    if progress_cb:
        await progress_cb(10.0, "Resolving stream metadata...")
    metadata = await validate_youtube_url(url)

    audio_path, duration, window_offset = await download_fast_audio(
        url=url,
        metadata=metadata,
        output_dir=output_dir,
        progress_cb=progress_cb,
    )

    if progress_cb:
        await progress_cb(80.0, "Detecting loudness & action peaks...")
    peaks = await asyncio.to_thread(detect_audio_energy_peaks, audio_path, 14)

    if progress_cb:
        await progress_cb(100.0, f"Scanned {duration:.0f}s • {len(peaks)} peaks")

    return IngestResult(
        metadata=metadata,
        url=url.strip(),
        audio_path=audio_path,
        duration=duration,
        window_offset=window_offset,
        peaks=peaks,
    )
