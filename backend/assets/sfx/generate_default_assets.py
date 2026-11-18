"""Synthesize clean, playable royalty-free SFX and fallback BGM tracks via NumPy + FFmpeg.

Ensures the studio runs end-to-end out of the box even without external API keys or
pre-populated user audio packs. Users can drop their own MP3/WAV files into
backend/assets/sfx/ and backend/assets/royalty_free_bgm/ at any time.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
import numpy as np

ASSETS_DIR = Path(__file__).resolve().parent.parent
SFX_DIR = ASSETS_DIR / "sfx"
BGM_DIR = ASSETS_DIR / "royalty_free_bgm"
SAMPLE_RATE = 44100


def _write_mp3(samples: np.ndarray, output_path: Path, sample_rate: int = SAMPLE_RATE) -> None:
    """Write stereo or mono float32 [-1, 1] numpy array to MP3 using FFmpeg (fallback to WAV)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    peak = float(np.max(np.abs(samples))) if samples.size else 1.0
    if peak > 0.98:
        samples = samples / peak * 0.95
    pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)

    channels = 1 if pcm.ndim == 1 else pcm.shape[1]
    ffmpeg = shutil.which("ffmpeg")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)

    try:
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm.tobytes())

        if ffmpeg and output_path.suffix.lower() == ".mp3":
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-loglevel",
                    "error",
                    "-i",
                    str(wav_path),
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "192k",
                    str(output_path),
                ],
                check=True,
            )
        else:
            shutil.copyfile(wav_path, output_path)
    finally:
        if wav_path.exists():
            wav_path.unlink(missing_ok=True)


def _gen_vine_boom() -> np.ndarray:
    dur = 1.35
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    # Pitch-dropping 808 sub thump + transient punch
    freq = 125.0 * np.exp(-6.5 * t) + 36.0
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    sub = np.sin(phase) * np.exp(-2.6 * t)
    click = np.sin(2 * np.pi * 240 * t) * np.exp(-42.0 * t) * 0.55
    grit = np.tanh((sub + click) * 2.2) * 0.85
    return np.column_stack([grit, grit])


def _gen_whoosh() -> np.ndarray:
    dur = 0.75
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 1, n)
    # Moving bandpass-like tonal sweep + filtered noise envelope
    env = np.sin(np.pi * (t / dur)) ** 1.6
    sweep_freq = 180 + 1600 * (t / dur) ** 1.5
    sweep = np.sin(2 * np.pi * np.cumsum(sweep_freq) / SAMPLE_RATE) * 0.25
    # Simple moving average smoothing for smooth air whoosh
    kernel = np.ones(18) / 18.0
    smooth_noise = np.convolve(noise, kernel, mode="same")
    sig = (smooth_noise * 0.75 + sweep) * env
    return np.column_stack([sig, sig * 0.96])


def _gen_bruh() -> np.ndarray:
    dur = 0.9
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    # Comedic downward brass/horn formant drop
    freq = 145.0 - 55.0 * (t / dur) ** 0.7
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    horn = (
        0.55 * np.sin(phase)
        + 0.30 * np.sin(2 * phase)
        + 0.18 * np.sin(3 * phase)
        + 0.10 * np.sin(4 * phase)
    )
    env = np.minimum(1.0, t / 0.03) * np.exp(-2.4 * t)
    sig = np.tanh(horn * 1.4) * env * 0.85
    return np.column_stack([sig, sig])


def _gen_wasted_hit() -> np.ndarray:
    dur = 2.2
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    # Iconic deep cinematic metallic impact + dark low drone
    sub = np.sin(2 * np.pi * 44.0 * t) * np.exp(-1.2 * t)
    metal = (
        np.sin(2 * np.pi * 110.0 * t) * 0.35
        + np.sin(2 * np.pi * 155.56 * t) * 0.28
        + np.sin(2 * np.pi * 233.08 * t) * 0.20
    ) * np.exp(-1.9 * t)
    impact = np.sin(2 * np.pi * (180 * np.exp(-12 * t) + 32) * t) * np.exp(-6.0 * t)
    sig = np.tanh((sub * 0.7 + metal * 0.6 + impact * 0.8) * 1.5) * 0.85
    return np.column_stack([sig, sig])


def _gen_bass_drop() -> np.ndarray:
    dur = 1.1
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    freq = 95.0 * np.exp(-5.0 * t) + 34.0
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    sig = np.tanh(np.sin(phase) * 2.5) * np.exp(-2.2 * t) * 0.88
    return np.column_stack([sig, sig])


def _gen_phonk_loop(bpm: float = 130.0, duration: float = 34.0) -> np.ndarray:
    """High-energy drift phonk style 808 kick + cowbell melody + crisp hi-hats."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    beat_sec = 60.0 / bpm
    mix_l = np.zeros(n, dtype=np.float64)
    mix_r = np.zeros(n, dtype=np.float64)

    # Cowbell riff notes (D minor pentatonic phrygian)
    riff_hz = [587.33, 622.25, 587.33, 523.25, 440.0, 523.25, 587.33, 783.99]
    total_beats = int(duration / beat_sec)

    for b in range(total_beats):
        start_idx = int(b * beat_sec * SAMPLE_RATE)
        if start_idx >= n:
            break

        # 808 Kick on every beat, extra heavy drop every 4th beat
        kick_len = min(int(0.32 * SAMPLE_RATE), n - start_idx)
        kt = np.linspace(0, kick_len / SAMPLE_RATE, kick_len, endpoint=False)
        k_freq = (130.0 if b % 4 == 0 else 105.0) * np.exp(-14.0 * kt) + 38.0
        k_phase = 2 * np.pi * np.cumsum(k_freq) / SAMPLE_RATE
        kick = np.tanh(np.sin(k_phase) * (2.6 if b % 4 == 0 else 1.8)) * np.exp(-5.2 * kt) * 0.65
        mix_l[start_idx : start_idx + kick_len] += kick
        mix_r[start_idx : start_idx + kick_len] += kick

        # Phonk metallic cowbell on half-beat subdivisions
        for sub in (0.0, 0.5):
            cb_start = int((b + sub) * beat_sec * SAMPLE_RATE)
            if cb_start >= n:
                continue
            cb_len = min(int(0.18 * SAMPLE_RATE), n - cb_start)
            ct = np.linspace(0, cb_len / SAMPLE_RATE, cb_len, endpoint=False)
            note = riff_hz[(b * 2 + int(sub * 2)) % len(riff_hz)]
            cb = (np.sign(np.sin(2 * np.pi * note * ct)) * 0.5 + np.sin(2 * np.pi * note * 1.48 * ct) * 0.5)
            cb *= np.exp(-16.0 * ct) * 0.22
            pan = 0.6 if (b % 2 == 0) else 0.4
            mix_l[cb_start : cb_start + cb_len] += cb * pan
            mix_r[cb_start : cb_start + cb_len] += cb * (1.0 - pan)

        # Snare / clap on beats 1 and 3 (off-beats)
        if b % 2 == 1:
            sn_len = min(int(0.14 * SAMPLE_RATE), n - start_idx)
            rng = np.random.default_rng(100 + b)
            st = np.linspace(0, sn_len / SAMPLE_RATE, sn_len, endpoint=False)
            snare = rng.normal(0, 1, sn_len) * np.exp(-22.0 * st) * 0.28
            mix_l[start_idx : start_idx + sn_len] += snare
            mix_r[start_idx : start_idx + sn_len] += snare

    # Subtle dark synth bassline
    bass_freq = np.where((t % (beat_sec * 8)) < (beat_sec * 4), 55.0, 48.999)
    bass = np.sin(2 * np.pi * np.cumsum(bass_freq) / SAMPLE_RATE) * 0.20
    mix_l = np.tanh((mix_l + bass) * 1.1) * 0.85
    mix_r = np.tanh((mix_r + bass) * 1.1) * 0.85
    return np.column_stack([mix_l, mix_r])


def _gen_cinematic_loop(bpm: float = 96.0, duration: float = 34.0) -> np.ndarray:
    """Vice City neon synthwave pad + deep cinematic pulse."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    beat_sec = 60.0 / bpm

    # Lush synthwave chord progression (Am - F - C - G)
    chords = [
        [220.0, 261.63, 329.63],
        [174.61, 220.0, 261.63],
        [130.81, 196.0, 261.63],
        [196.0, 246.94, 293.66],
    ]
    bar_sec = beat_sec * 4
    pad_l = np.zeros(n, dtype=np.float64)
    pad_r = np.zeros(n, dtype=np.float64)

    for i, chord in enumerate(chords):
        mask = ((t // bar_sec).astype(int) % len(chords)) == i
        for freq in chord:
            pad_l[mask] += np.sin(2 * np.pi * freq * t[mask]) * 0.14
            pad_r[mask] += np.sin(2 * np.pi * (freq * 1.004) * t[mask]) * 0.14

    # Sidechain pumping pulse synced to BPM
    beat_phase = (t % beat_sec) / beat_sec
    sidechain = 0.35 + 0.65 * np.minimum(1.0, beat_phase * 2.5)
    pad_l *= sidechain
    pad_r *= sidechain

    # Deep cinematic kick every beat
    total_beats = int(duration / beat_sec)
    for b in range(total_beats):
        start_idx = int(b * beat_sec * SAMPLE_RATE)
        k_len = min(int(0.28 * SAMPLE_RATE), n - start_idx)
        kt = np.linspace(0, k_len / SAMPLE_RATE, k_len, endpoint=False)
        k_freq = 90.0 * np.exp(-10.0 * kt) + 40.0
        kick = np.sin(2 * np.pi * np.cumsum(k_freq) / SAMPLE_RATE) * np.exp(-6.0 * kt) * 0.5
        pad_l[start_idx : start_idx + k_len] += kick
        pad_r[start_idx : start_idx + k_len] += kick

    return np.column_stack([np.tanh(pad_l) * 0.82, np.tanh(pad_r) * 0.82])


def _gen_meme_bounce_loop(bpm: float = 128.0, duration: float = 34.0) -> np.ndarray:
    """Playful bouncy trap-meme groove with punchy bass hits."""
    n = int(SAMPLE_RATE * duration)
    beat_sec = 60.0 / bpm
    mix_l = np.zeros(n, dtype=np.float64)
    mix_r = np.zeros(n, dtype=np.float64)
    notes = [329.63, 392.0, 440.0, 523.25, 493.88, 392.0, 329.63, 293.66]
    total_beats = int(duration / beat_sec)

    for b in range(total_beats):
        start_idx = int(b * beat_sec * SAMPLE_RATE)
        if start_idx >= n:
            break
        k_len = min(int(0.24 * SAMPLE_RATE), n - start_idx)
        kt = np.linspace(0, k_len / SAMPLE_RATE, k_len, endpoint=False)
        kick = np.sin(2 * np.pi * np.cumsum(115 * np.exp(-15 * kt) + 45) / SAMPLE_RATE) * np.exp(-8 * kt) * 0.58
        mix_l[start_idx : start_idx + k_len] += kick
        mix_r[start_idx : start_idx + k_len] += kick

        # Plucky synth melody
        p_len = min(int(0.2 * SAMPLE_RATE), n - start_idx)
        pt = np.linspace(0, p_len / SAMPLE_RATE, p_len, endpoint=False)
        note = notes[b % len(notes)]
        pluck = (np.sin(2 * np.pi * note * pt) + 0.4 * np.sin(4 * np.pi * note * pt)) * np.exp(-11 * pt) * 0.25
        mix_l[start_idx : start_idx + p_len] += pluck
        mix_r[start_idx : start_idx + p_len] += pluck * 0.9

    return np.column_stack([np.tanh(mix_l) * 0.84, np.tanh(mix_r) * 0.84])


def ensure_default_assets() -> dict[str, list[str]]:
    """Generate default SFX and royalty-free BGM files if they don't exist yet."""
    generated_sfx: list[str] = []
    generated_bgm: list[str] = []

    sfx_builders = {
        "vine_boom.mp3": _gen_vine_boom,
        "whoosh.mp3": _gen_whoosh,
        "bruh.mp3": _gen_bruh,
        "wasted_hit.mp3": _gen_wasted_hit,
        "bass_drop.mp3": _gen_bass_drop,
    }
    for fname, fn in sfx_builders.items():
        path = SFX_DIR / fname
        if not path.exists() or path.stat().st_size < 512:
            _write_mp3(fn(), path)
            generated_sfx.append(str(path))

    bgm_builders = {
        "vice_phonk_130bpm.mp3": lambda: _gen_phonk_loop(130.0, 34.0),
        "sunset_cinematic_96bpm.mp3": lambda: _gen_cinematic_loop(96.0, 34.0),
        "chaotic_meme_128bpm.mp3": lambda: _gen_meme_bounce_loop(128.0, 34.0),
    }
    for fname, fn in bgm_builders.items():
        path = BGM_DIR / fname
        if not path.exists() or path.stat().st_size < 1024:
            _write_mp3(fn(), path)
            generated_bgm.append(str(path))

    return {"sfx": generated_sfx, "bgm": generated_bgm}


if __name__ == "__main__":
    result = ensure_default_assets()
    print("Ensured default studio audio assets:", result)
