"""Beat, onset, and sub-bass drop extraction powered by librosa."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Tuple

import librosa
import numpy as np

from models import BeatMarker


def _analyze_sync(
    audio_path: Path,
    clip_duration: float,
    min_beat_gap: float = 0.35,
) -> Tuple[float, list[BeatMarker]]:
    """Extract BPM, beat timestamps, onset strength, and bass-drop peaks within clip_duration."""
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True, duration=max(clip_duration + 2.0, 20.0))
    if y.size == 0:
        return 128.0, _synthetic_beats(clip_duration, 128.0)

    hop_length = 512
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    tempo, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop_length,
        trim=False,
    )

    bpm = float(np.atleast_1d(tempo)[0]) if tempo is not None else 128.0
    if bpm < 70 or bpm > 190:
        bpm = 128.0

    # Sub-bass energy envelope (20Hz - 160Hz) to pinpoint heavy 808 drops
    stft = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop_length))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    bass_mask = (freqs >= 20.0) & (freqs <= 165.0)
    bass_energy = np.mean(stft[bass_mask, :], axis=0) if np.any(bass_mask) else onset_env
    if bass_energy.max() > 0:
        bass_energy = bass_energy / bass_energy.max()
    if onset_env.max() > 0:
        onset_norm = onset_env / onset_env.max()
    else:
        onset_norm = np.ones_like(onset_env) * 0.5

    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)

    # Compute combined hit intensity at each detected beat
    raw_markers: list[tuple[float, float]] = []
    for frame_idx, t in zip(beat_frames, beat_times):
        t_val = float(t)
        if t_val < 0.25 or t_val > clip_duration - 0.15:
            continue
        f_idx = min(int(frame_idx), len(onset_norm) - 1, len(bass_energy) - 1)
        # Local peak window (±2 frames)
        lo = max(0, f_idx - 2)
        hi = min(len(bass_energy), f_idx + 3)
        strength = float(0.55 * np.max(bass_energy[lo:hi]) + 0.45 * np.max(onset_norm[lo:hi]))
        raw_markers.append((t_val, min(1.0, max(0.15, strength))))

    if not raw_markers:
        return bpm, _synthetic_beats(clip_duration, bpm)

    # Determine bass-drop threshold (top ~25% strongest beats or every 4th bar anchor)
    strengths = np.array([s for _, s in raw_markers], dtype=np.float32)
    drop_threshold = float(np.percentile(strengths, 72))

    markers: list[BeatMarker] = []
    last_time = -999.0
    last_drop_time = -999.0
    for idx, (t_val, strength) in enumerate(raw_markers):
        if t_val - last_time < min_beat_gap:
            continue
        is_drop = (strength >= drop_threshold or idx % 4 == 0) and (t_val - last_drop_time >= 1.45)
        if is_drop:
            last_drop_time = t_val
        markers.append(
            BeatMarker(
                time=round(t_val, 3),
                strength=round(strength, 3),
                is_drop=is_drop,
            )
        )
        last_time = t_val

    return round(bpm, 1), markers


def _synthetic_beats(duration: float, bpm: float = 128.0) -> list[BeatMarker]:
    """Deterministic BPM grid fallback if audio analysis yields sparse beats."""
    step = 60.0 / max(bpm, 80.0)
    markers: list[BeatMarker] = []
    t = step
    idx = 0
    while t < duration - 0.2:
        is_drop = idx % 4 == 0
        markers.append(
            BeatMarker(
                time=round(t, 3),
                strength=0.95 if is_drop else 0.62,
                is_drop=is_drop,
            )
        )
        t += step
        idx += 1
    return markers


async def extract_beat_markers(
    audio_path: Path,
    clip_duration: float,
) -> Tuple[float, list[BeatMarker]]:
    """Async wrapper for librosa beat and bass-drop detection."""
    try:
        return await asyncio.to_thread(_analyze_sync, audio_path, clip_duration)
    except Exception:
        return 128.0, _synthetic_beats(clip_duration, 128.0)
