"""Fast AI Creative Director: Cached Faster-Whisper + Google Gemini (gemini-4-hydrogen) Clip Selector."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Optional

from models import (
    EmotionTag,
    GeminiDirectorOutput,
    GeminiSelectedClip,
    MemeCue,
    NarrativeAnnotation,
    SpeedRampSegment,
    StylePreset,
    WordCaption,
)
from pipeline.stream_ingestor import EnergyPeak

ASSETS_MEMES_MANIFEST = Path(__file__).resolve().parent.parent / "assets" / "memes" / "triggers.json"
ProgressCallback = Optional[Callable[[float, str], Awaitable[None]]]

_WHISPER_MODEL_CACHE: dict[str, object] = {}

RED_KEYWORDS = {
    "wasted", "dead", "died", "killed", "exploded", "explosion", "busted", "crash",
    "crashed", "police", "cops", "swat", "insane", "crazy", "regret", "cooked", "rip",
}
CYAN_KEYWORDS = {
    "gta", "vice", "leonida", "lucia", "jason", "six", "6", "five", "stars", "wanted",
    "drift", "nitro", "clutch", "clean", "stunt", "heist", "speed", "escape",
}
YELLOW_KEYWORDS = {
    "bro", "what", "wait", "no", "way", "bruh", "watch", "look", "actually", "literally",
    "never", "tried", "really", "yo", "oh", "my", "god",
}


@dataclass
class TranscriptWord:
    word: str
    start: float
    end: float


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    words: list[TranscriptWord]


def _load_meme_catalog() -> dict[str, dict]:
    if ASSETS_MEMES_MANIFEST.exists():
        data = json.loads(ASSETS_MEMES_MANIFEST.read_text(encoding="utf-8"))
        return {m["type"]: m for m in data.get("memes", [])}
    return {}


def _classify_word_style(word: str) -> tuple[bool, str]:
    clean = "".join(ch for ch in word.lower() if ch.isalnum())
    if clean in RED_KEYWORDS:
        return True, "red"
    if clean in CYAN_KEYWORDS:
        return True, "cyan"
    if clean in YELLOW_KEYWORDS or word.endswith("!") or word.endswith("?"):
        return True, "yellow"
    return False, "yellow"


def _get_whisper_model():
    """Load & cache Faster-Whisper once in memory (defaults to ultra-fast 'tiny' on CPU)."""
    from faster_whisper import WhisperModel

    model_size = os.getenv("WHISPER_MODEL_SIZE", "tiny").strip() or "tiny"
    device = os.getenv("WHISPER_DEVICE", "cpu").strip() or "cpu"
    if device == "auto":
        device = "cpu"
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8").strip() or "int8"

    key = f"{model_size}:{device}:{compute_type}"
    if key not in _WHISPER_MODEL_CACHE:
        _WHISPER_MODEL_CACHE[key] = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=max(2, os.cpu_count() or 4),
        )
    return _WHISPER_MODEL_CACHE[key]


def transcribe_clip_audio_sync(audio_path: Path, start_sec: float, duration: float) -> list[WordCaption]:
    """Ultra-fast word-level transcription on ONLY a single 15-30s clip (~1-2s on CPU!)."""
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        clip_wav = Path(tmp.name)

    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-ss",
                f"{max(0.0, start_sec):.2f}",
                "-t",
                f"{duration:.2f}",
                "-i",
                str(audio_path),
                "-ac",
                "1",
                "-ar",
                "16000",
                str(clip_wav),
            ],
            check=True,
        )

        model = _get_whisper_model()
        segments_iter, _ = model.transcribe(
            str(clip_wav),
            word_timestamps=True,
            vad_filter=True,
            beam_size=1,
            best_of=1,
        )
        captions: list[WordCaption] = []
        for seg in segments_iter:
            if seg.words:
                for w in seg.words:
                    text = (w.word or "").strip()
                    if not text:
                        continue
                    rel_s = max(0.0, float(w.start))
                    rel_e = min(duration, max(rel_s + 0.08, float(w.end)))
                    emphasis, color = _classify_word_style(text)
                    captions.append(
                        WordCaption(
                            word=text.upper(),
                            start=round(rel_s, 3),
                            end=round(rel_e, 3),
                            emphasis=emphasis,
                            color=color,  # type: ignore[arg-type]
                        )
                    )
        if captions:
            return captions
    except Exception:
        pass
    finally:
        clip_wav.unlink(missing_ok=True)

    # Rhythmic fallback for pure gameplay with no speech
    fallback_lines = [
        "NO WAY", "HE ACTUALLY", "SENT IT", "FULL THROTTLE", "IN VICE CITY",
        "WAIT FOR", "THE IMPACT", "BRO IS COOKED", "FIVE STARS", "INSTANT CHAOS",
    ]
    step = duration / len(fallback_lines)
    return [
        WordCaption(
            word=phrase,
            start=round(i * step + 0.2, 3),
            end=round(min(duration - 0.1, (i + 1) * step - 0.1), 3),
            emphasis=(i % 3 == 0),
            color="cyan" if i % 3 == 0 else ("red" if i == 7 else "yellow"),  # type: ignore[arg-type]
        )
        for i, phrase in enumerate(fallback_lines)
    ]


def _preset_default_emotion(preset: StylePreset) -> EmotionTag:
    if preset == StylePreset.FIREFLY_CINEMATIC:
        return EmotionTag.EPIC_CINEMATIC
    if preset == StylePreset.CHAOTIC_MEME:
        return EmotionTag.FUNNY_MEME
    return EmotionTag.HYPE_PHONK


def _call_gemini_director_sync(
    peaks: list[EnergyPeak],
    video_duration: float,
    num_shorts: int,
    preset: StylePreset,
    stream_title: str,
) -> Optional[GeminiDirectorOutput]:
    """Call Google Gemini API (google-genai Interactions API, gemini-4-hydrogen) with structured JSON."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        return None

    try:
        from google import genai
    except ImportError:
        return None

    model_name = os.getenv("GEMINI_MODEL", "gemini-4-hydrogen").strip() or "gemini-4-hydrogen"
    if model_name.startswith(("gemini-2.5", "gemini-2.0", "gemini-1.5")):
        model_name = "gemini-4-hydrogen"

    peak_lines = [
        f"- {p.time_sec:.1f}s (loudness={p.audio_score:.2f}, peak={p.motion_score:.2f})"
        for p in peaks[:12]
    ]

    prompt_text = f"""You are an elite viral Gen-Z GTA 6 Shorts Creative Director (Strykeditz / Firefly edit style).

Stream Title: {stream_title}
Scanned Audio Duration: {video_duration:.1f} seconds
Style Preset: {preset.value}
Requested Shorts Count: {num_shorts}

TOP HIGH-ENERGY AUDIO PEAKS:
{chr(10).join(peak_lines) or "Distribute evenly across duration."}

RULES:
1. Return EXACTLY {num_shorts} distinct, non-overlapping clips within [0.0, {video_duration:.1f}].
2. EVERY clip duration (end_sec - start_sec) MUST be STRICTLY 15.0 to 30.0 seconds (ideal: 18-24s).
3. Center each clip slightly before a top energy peak so the buildup leads into the drop.
4. Write a punchy ALL-CAPS curiosity hook (<= 48 chars, 1-2 emojis) for `hook_banner_text`.
5. Add 2 Firefly-style uppercase italic annotations (`*WAIT FOR IT...*`, `*INSTANT REGRET*`).
6. Add 2 meme cues (`gta_wasted_overlay`, `vine_boom_shockwave`, `zoom_freeze_frame`, `skull_reaction`, `police_siren_flash`, `mission_passed`).
7. Add 1 speed ramp (`speed: 0.45`, ~1.4s) at the climax moment.
"""

    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=model_name,
        input=prompt_text,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": GeminiDirectorOutput.model_json_schema(),
        },
    )

    if not interaction.output_text:
        return None
    return GeminiDirectorOutput.model_validate_json(interaction.output_text)


def _heuristic_select_clips(
    peaks: list[EnergyPeak],
    video_duration: float,
    num_shorts: int,
    preset: StylePreset,
) -> list[GeminiSelectedClip]:
    """Fast deterministic peak-based clip selection fallback."""
    default_emotion = _preset_default_emotion(preset).value
    hook_templates = [
        "BRO REALLY TRIED THIS IN GTA 6 💀🔥",
        "5-STAR CHASE WENT WRONG INSTANTLY 🚨💀",
        "GTA 6 PHYSICS JUST BROKE REALITY 🤯🔥",
        "WAIT UNTIL THE POLICE SHOW UP 💀🚓",
        "HE THOUGHT HE ESCAPED VICE CITY 😭🔥",
        "ZERO CHANCE HE SURVIVED THAT CRASH 💀💥",
    ]
    note_sets = [
        [("*WAIT FOR IT...*", 2.0, 4.6, "upper"), ("*INSTANT REGRET*", 10.5, 13.8, "upper")],
        [("*5-STAR LOCKDOWN*", 3.0, 5.8, "upper"), ("*POLICE SURROUNDED HIM*", 12.0, 15.2, "upper")],
        [("*FULL THROTTLE*", 2.4, 5.0, "upper"), ("*NO BRAKES*", 11.2, 14.5, "upper")],
    ]

    safe_dur = max(18.0, video_duration)
    target_len = min(22.0, max(16.0, safe_dur / max(1, num_shorts) if safe_dur > 30 else safe_dur))
    target_len = max(15.0, min(26.0, target_len))

    centers: list[float] = []
    for p in peaks:
        if all(abs(p.time_sec - c) >= 16.0 for c in centers):
            centers.append(p.time_sec)
        if len(centers) >= num_shorts:
            break

    while len(centers) < num_shorts:
        idx = len(centers)
        centers.append((idx + 0.5) * (safe_dur / max(1, num_shorts)))

    clips: list[GeminiSelectedClip] = []
    for i, center in enumerate(centers[:num_shorts]):
        start_s = max(0.0, center - target_len * 0.35)
        end_s = min(safe_dur, start_s + target_len)
        if end_s - start_s < 15.0:
            start_s = max(0.0, end_s - 15.0)
            end_s = min(safe_dur, start_s + 15.0)
        clip_dur = max(15.0, min(30.0, end_s - start_s))
        end_s = start_s + clip_dur

        notes = note_sets[i % len(note_sets)]
        climax_t = round(clip_dur * 0.58, 2)
        meme_type = (
            "gta_wasted_overlay"
            if i % 3 == 0
            else "police_siren_flash"
            if i % 3 == 1
            else "zoom_freeze_frame"
        )

        clips.append(
            GeminiSelectedClip(
                start_sec=round(start_s, 2),
                end_sec=round(end_s, 2),
                title=f"Vice City Highlight #{i + 1}",
                hook_banner_text=hook_templates[i % len(hook_templates)],
                viral_score=max(85, 97 - i * 2),
                viral_reason=f"Peak energy spike at {center:.1f}s",
                emotion=default_emotion,  # type: ignore[arg-type]
                annotations=[
                    {
                        "text": txt,
                        "relative_start": min(clip_dur - 3.0, rs),
                        "relative_end": min(clip_dur - 0.5, re),
                        "position": pos,
                    }
                    for txt, rs, re, pos in notes
                ],
                memes=[
                    {
                        "type": "vine_boom_shockwave",
                        "label": "VINE BOOM",
                        "relative_time": round(min(4.0, clip_dur * 0.22), 2),
                        "duration": 0.9,
                        "freeze_frame": False,
                    },
                    {
                        "type": meme_type,
                        "label": "WASTED" if meme_type == "gta_wasted_overlay" else "5-STAR CHAOS",
                        "relative_time": climax_t,
                        "duration": 1.8,
                        "freeze_frame": meme_type in ("gta_wasted_overlay", "zoom_freeze_frame"),
                    },
                ],
                speed_ramps=[
                    {
                        "relative_start": max(2.0, climax_t - 0.5),
                        "relative_end": min(clip_dur - 1.0, climax_t + 0.9),
                        "speed": 0.45,
                    }
                ],
            )
        )
    return clips


def _clamp_and_enrich_clips(
    raw_clips: list[GeminiSelectedClip],
    video_duration: float,
    num_shorts: int,
    public_base_url: str,
) -> list[dict]:
    meme_catalog = _load_meme_catalog()
    enriched: list[dict] = []

    for idx, clip in enumerate(raw_clips[:num_shorts]):
        start_s = max(0.0, float(clip.start_sec))
        end_s = float(clip.end_sec)
        dur = end_s - start_s

        if video_duration < 15.0:
            start_s = 0.0
            end_s = max(5.0, video_duration)
        elif dur < 15.0:
            end_s = min(max(video_duration, start_s + 15.0), start_s + 18.0)
            if end_s - start_s < 15.0:
                start_s = max(0.0, end_s - 15.0)
        elif dur > 30.0:
            end_s = start_s + 26.0

        dur = round(max(5.0, min(30.0, end_s - start_s)), 2)
        end_s = round(start_s + dur, 2)

        annotations: list[NarrativeAnnotation] = []
        for ann in clip.annotations[:3]:
            a_start = round(max(0.4, min(dur - 1.4, float(ann.relative_start))), 2)
            a_end = round(max(a_start + 0.9, min(dur - 0.15, float(ann.relative_end))), 2)
            txt = ann.text.strip().upper()
            if not txt.startswith("*"):
                txt = f"*{txt}*"
            annotations.append(
                NarrativeAnnotation(text=txt, start=a_start, end=a_end, position=ann.position)
            )

        memes: list[MemeCue] = []
        for m_idx, m in enumerate(clip.memes[:3]):
            spec = meme_catalog.get(m.type, {})
            sfx_name = spec.get("default_sfx", "vine_boom.mp3")
            t = max(0.6, min(dur - 1.0, float(m.relative_time)))
            memes.append(
                MemeCue(
                    id=f"meme_{idx}_{m_idx}_{m.type}",
                    type=m.type,
                    label=(m.label or spec.get("label", "BOOM")).upper(),
                    time=round(t, 2),
                    duration=round(max(0.5, min(3.0, float(m.duration))), 2),
                    sfx=sfx_name,
                    sfx_url=f"{public_base_url}/assets/sfx/{sfx_name}",
                    freeze_frame=bool(m.freeze_frame or spec.get("freeze_frame", False)),
                    intensity=float(spec.get("intensity", 0.9)),
                )
            )

        ramps: list[SpeedRampSegment] = []
        for r in clip.speed_ramps[:1]:
            r_start = round(max(1.0, min(dur - 2.0, float(r.relative_start))), 2)
            r_end = round(max(r_start + 0.7, min(dur - 0.4, float(r.relative_end))), 2)
            ramps.append(
                SpeedRampSegment(
                    start=r_start,
                    end=r_end,
                    speed=round(max(0.35, min(0.85, float(r.speed))), 2),
                )
            )

        enriched.append({
            "index": idx + 1,
            "start_sec": round(start_s, 2),
            "end_sec": round(end_s, 2),
            "duration": dur,
            "title": clip.title,
            "hook_banner_text": clip.hook_banner_text.upper()[:64],
            "viral_score": int(clip.viral_score),
            "viral_reason": clip.viral_reason,
            "emotion": EmotionTag(clip.emotion),
            "annotations": annotations,
            "memes": memes,
            "speed_ramps": ramps,
        })
    return enriched


async def direct_viral_clips(
    peaks: list[EnergyPeak],
    video_duration: float,
    num_shorts: int,
    preset: StylePreset,
    stream_title: str,
    public_base_url: str,
    progress_cb: ProgressCallback = None,
) -> list[dict]:
    """Fast Stage 2: Gemini AI Director selects exact 15-30s viral windows in ~2-3 seconds."""
    if progress_cb:
        await progress_cb(30.0, f"AI Director selecting top {num_shorts} clips...")

    gemini_result: Optional[GeminiDirectorOutput] = None
    try:
        gemini_result = await asyncio.wait_for(
            asyncio.to_thread(
                _call_gemini_director_sync,
                peaks,
                video_duration,
                num_shorts,
                preset,
                stream_title,
            ),
            timeout=25.0,
        )
    except Exception:
        gemini_result = None

    if gemini_result and gemini_result.clips:
        selected = list(gemini_result.clips)
        if len(selected) < num_shorts:
            extras = _heuristic_select_clips(peaks, video_duration, num_shorts, preset)
            selected += extras[len(selected) : num_shorts]
        source_note = "Gemini AI"
    else:
        selected = _heuristic_select_clips(peaks, video_duration, num_shorts, preset)
        source_note = "Peak Director"

    blueprints = _clamp_and_enrich_clips(selected, video_duration, num_shorts, public_base_url)

    if progress_cb:
        await progress_cb(100.0, f"Selected {len(blueprints)} clips ({source_note})")

    return blueprints
