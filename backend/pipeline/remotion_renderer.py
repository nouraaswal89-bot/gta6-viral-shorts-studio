"""Fast 1080x1920 MP4 Exporter with cross-platform font support + 2-line wrapped Top Hook Banner."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Optional

from models import ShortClipData

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
RENDER_SCRIPT = FRONTEND_DIR / "src" / "remotion" / "render-cli.mjs"


def _find_bold_font() -> Optional[str]:
    """Locate a reliable bold sans-serif TTF across Linux Docker (Railway) and Windows."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            # Escape Windows drive colon for FFmpeg drawtext fontfile syntax
            return path.replace("\\", "/").replace(":", "\\:")
    return None


def _escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace("\n", " ")
    )


def _render_via_remotion_sync(clip: ShortClipData, props_path: Path, output_mp4: Path) -> bool:
    if os.getenv("ENABLE_REMOTION_RENDER", "false").lower() != "true":
        return False
    node_bin = shutil.which("node")
    if not node_bin or not RENDER_SCRIPT.exists():
        return False
    if not (FRONTEND_DIR / "node_modules" / "@remotion" / "renderer").exists():
        return False

    props_path.write_text(clip.model_dump_json(indent=2), encoding="utf-8")
    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        node_bin,
        str(RENDER_SCRIPT),
        "--props",
        str(props_path),
        "--output",
        str(output_mp4),
    ]
    try:
        res = subprocess.run(cmd, cwd=str(FRONTEND_DIR), capture_output=True, text=True, timeout=180)
        return res.returncode == 0 and output_mp4.exists() and output_mp4.stat().st_size > 20000
    except Exception:
        return False


def _render_via_ffmpeg_fast_sync(
    enhanced_video: Path,
    clip: ShortClipData,
    output_mp4: Path,
) -> Path:
    """Blazing-fast (~2-4s) 1080x1920 MP4 compositor with Top White Curiosity Hook Banner."""
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    clean_hook = (
        clip.hook_banner_text.encode("ascii", "ignore").decode("ascii").strip()
        or "GTA 6 VIRAL MOMENT"
    )
    lines = textwrap.wrap(clean_hook, width=26)[:2] or ["GTA 6 VIRAL MOMENT"]
    font_path = _find_bold_font()
    font_opt = f"fontfile='{font_path}':" if font_path else ""

    filters = [
        "drawbox=x=0:y=0:w=iw:h=240:color=white@1.0:t=fill",
        "drawbox=x=0:y=234:w=iw:h=6:color=0xff2e93@1.0:t=fill",
    ]
    if len(lines) == 1:
        t1 = _escape_drawtext(lines[0])
        filters.append(
            f"drawtext={font_opt}text='{t1}':fontcolor=black:fontsize=50:x=(w-text_w)/2:y=(234-text_h)/2"
        )
    else:
        t1 = _escape_drawtext(lines[0])
        t2 = _escape_drawtext(lines[1])
        filters.append(
            f"drawtext={font_opt}text='{t1}':fontcolor=black:fontsize=46:x=(w-text_w)/2:y=64"
        )
        filters.append(
            f"drawtext={font_opt}text='{t2}':fontcolor=black:fontsize=46:x=(w-text_w)/2:y=128"
        )

    vf = ",".join(filters)
    cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(enhanced_video),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-profile:v",
        "high",
        "-level",
        "4.1",
        "-preset",
        "ultrafast",
        "-threads",
        "0",
        "-crf",
        "21",
        "-maxrate",
        "12M",
        "-bufsize",
        "24M",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(output_mp4),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not output_mp4.exists() or output_mp4.stat().st_size < 10000:
        shutil.copyfile(enhanced_video, output_mp4)
    return output_mp4


async def render_final_short_mp4(
    clip: ShortClipData,
    enhanced_video: Path,
    clip_dir: Path,
) -> tuple[Path, str]:
    props_path = clip_dir / "remotion_props.json"
    output_mp4 = clip_dir / f"gta6_short_{clip.index:02d}_{clip.clip_id}.mp4"

    used_remotion = await asyncio.to_thread(
        _render_via_remotion_sync, clip, props_path, output_mp4
    )
    if used_remotion:
        return output_mp4, "remotion"

    await asyncio.to_thread(
        _render_via_ffmpeg_fast_sync, enhanced_video, clip, output_mp4
    )
    return output_mp4, "ffmpeg_fast"
