"""Automated Copyright-Free Music Discovery & Download (Pixabay -> yt-dlp NCS/CC -> Local Library)."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Awaitable, Callable, Optional

import httpx

from assets.sfx.generate_default_assets import ensure_default_assets
from models import EmotionTag, MusicTrackInfo

ASSETS_BGM_DIR = Path(__file__).resolve().parent.parent / "assets" / "royalty_free_bgm"
ProgressCallback = Optional[Callable[[float, str], Awaitable[None]]]

EMOTION_SEARCH_QUERIES: dict[EmotionTag, list[str]] = {
    EmotionTag.HYPE_PHONK: [
        "drift phonk aggressive bass",
        "phonk trap workout hype",
        "dark electronic bass drop",
    ],
    EmotionTag.EPIC_CINEMATIC: [
        "synthwave neon night cinematic",
        "emotional synthwave vice city",
        "epic trailer orchestral electronic",
    ],
    EmotionTag.FUNNY_MEME: [
        "funny trap bounce upbeat",
        "comedic hip hop quirk meme",
        "playful bass beat gaming",
    ],
}

NCS_SEARCH_QUERIES: dict[EmotionTag, str] = {
    EmotionTag.HYPE_PHONK: "ytsearch3:NoCopyrightSounds phonk bass gaming music",
    EmotionTag.EPIC_CINEMATIC: "ytsearch3:NoCopyrightSounds synthwave cinematic gaming",
    EmotionTag.FUNNY_MEME: "ytsearch3:NoCopyrightSounds upbeat gaming trap",
}


async def _fetch_from_pixabay(emotion: EmotionTag, cache_dir: Path) -> Optional[MusicTrackInfo]:
    """Query Pixabay API for royalty-free music matching the emotion tag."""
    api_key = os.getenv("PIXABAY_API_KEY", "").strip()
    if not api_key:
        return None

    queries = EMOTION_SEARCH_QUERIES.get(emotion, ["gaming electronic"])
    cache_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=18.0) as client:
        for query in queries:
            try:
                # Pixabay audio endpoint
                resp = await client.get(
                    "https://pixabay.com/api/",
                    params={
                        "key": api_key,
                        "q": query,
                        "media_type": "music",
                        "per_page": 5,
                    },
                )
                if resp.status_code != 200:
                    continue
                payload = resp.json()
                hits = payload.get("hits") or []
                for hit in hits:
                    audio_url = hit.get("audio") or hit.get("previewURL") or hit.get("url")
                    if not audio_url or not str(audio_url).startswith("http"):
                        continue
                    track_id = hit.get("id", "track")
                    target_path = cache_dir / f"pixabay_{emotion.value}_{track_id}.mp3"
                    if not target_path.exists():
                        dl = await client.get(audio_url)
                        if dl.status_code == 200 and len(dl.content) > 8192:
                            target_path.write_bytes(dl.content)
                        else:
                            continue
                    return MusicTrackInfo(
                        title=hit.get("tags", f"Pixabay {emotion.value}").split(",")[0].title(),
                        artist=hit.get("user", "Pixabay Royalty-Free"),
                        source="pixabay",
                        emotion=emotion,
                        bpm=130.0 if emotion == EmotionTag.HYPE_PHONK else 112.0,
                        local_path=str(target_path),
                        url="",
                    )
            except Exception:
                continue
    return None


async def _fetch_from_yt_dlp_ncs(emotion: EmotionTag, cache_dir: Path) -> Optional[MusicTrackInfo]:
    """Fallback: fetch Creative Commons / NoCopyrightSounds track via yt-dlp."""
    if os.getenv("ENABLE_YTDLP_BGM_SEARCH", "false").lower() != "true":
        return None
    yt_dlp_bin = shutil.which("yt-dlp")
    if not yt_dlp_bin:
        return None

    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"ncs_{emotion.value}.mp3"
    if target.exists() and target.stat().st_size > 16384:
        return MusicTrackInfo(
            title=f"NCS {emotion.value.replace('_', ' ').title()}",
            artist="NoCopyrightSounds (CC)",
            source="yt_dlp_ncs",
            emotion=emotion,
            bpm=128.0,
            local_path=str(target),
            url="",
        )

    query = NCS_SEARCH_QUERIES.get(emotion, "ytsearch1:NoCopyrightSounds gaming music")

    def _run() -> bool:
        cmd = [
            yt_dlp_bin,
            "--no-warnings",
            "-x",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "192K",
            "--max-downloads",
            "1",
            "--match-filter",
            "duration > 35 & duration < 300",
            "-o",
            str(cache_dir / f"ncs_{emotion.value}.%(ext)s"),
            query,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        return res.returncode == 0 and target.exists()

    try:
        ok = await asyncio.to_thread(_run)
        if ok:
            return MusicTrackInfo(
                title=f"NCS {emotion.value.replace('_', ' ').title()}",
                artist="NoCopyrightSounds (Royalty-Free)",
                source="yt_dlp_ncs",
                emotion=emotion,
                bpm=128.0,
                local_path=str(target),
                url="",
            )
    except Exception:
        return None
    return None


def _load_from_local_library(emotion: EmotionTag) -> MusicTrackInfo:
    """Load from assets/royalty_free_bgm/ catalog (auto-generating defaults if missing)."""
    ensure_default_assets()
    catalog_path = ASSETS_BGM_DIR / "catalog.json"
    if catalog_path.exists():
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        tracks = data.get("tracks", [])
        for track in tracks:
            if track.get("emotion") == emotion.value:
                file_path = ASSETS_BGM_DIR / track["file"]
                if file_path.exists():
                    return MusicTrackInfo(
                        title=track["title"],
                        artist=track.get("artist", "Royalty-Free Library"),
                        source="local_library",
                        emotion=emotion,
                        bpm=float(track.get("bpm", 128.0)),
                        local_path=str(file_path),
                        url=f"/assets/royalty_free_bgm/{track['file']}",
                    )

    # Scan any custom MP3/WAV placed by user into assets/royalty_free_bgm/
    audio_files = list(ASSETS_BGM_DIR.glob("*.mp3")) + list(ASSETS_BGM_DIR.glob("*.wav"))
    if audio_files:
        chosen = audio_files[0]
        return MusicTrackInfo(
            title=chosen.stem.replace("_", " ").title(),
            artist="Local Royalty-Free Pack",
            source="local_library",
            emotion=emotion,
            bpm=128.0,
            local_path=str(chosen),
            url=f"/assets/royalty_free_bgm/{chosen.name}",
        )

    raise FileNotFoundError("No royalty-free BGM tracks available in assets/royalty_free_bgm/.")


async def fetch_copyright_free_bgm(
    emotion: EmotionTag,
    job_dir: Path,
    public_base_url: str,
    progress_cb: ProgressCallback = None,
) -> MusicTrackInfo:
    """Resolve the best copyright-free BGM for a given clip emotion tag."""
    bgm_cache = job_dir / "bgm"
    bgm_cache.mkdir(parents=True, exist_ok=True)

    if progress_cb:
        await progress_cb(25.0, f"Searching copyright-free BGM for vibe '{emotion.value}'...")

    track = await _fetch_from_pixabay(emotion, bgm_cache)
    if track:
        track.url = f"{public_base_url}/workspace/{job_dir.name}/bgm/{Path(track.local_path).name}"
        if progress_cb:
            await progress_cb(100.0, f"Matched Pixabay track: {track.title}")
        return track

    track = await _fetch_from_yt_dlp_ncs(emotion, bgm_cache)
    if track:
        track.url = f"{public_base_url}/workspace/{job_dir.name}/bgm/{Path(track.local_path).name}"
        if progress_cb:
            await progress_cb(100.0, f"Matched NCS Creative Commons track: {track.title}")
        return track

    track = await asyncio.to_thread(_load_from_local_library, emotion)
    track.url = f"{public_base_url}{track.url}" if track.url.startswith("/") else track.url
    if progress_cb:
        await progress_cb(100.0, f"Loaded royalty-free library track: {track.title}")
    return track
