"""ffmpeg wrapper: MP4 -> 16kHz mono WAV (vstup pro Whisper)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _ffmpeg_bin() -> str:
    return os.environ.get("FFMPEG_PATH", "ffmpeg")


def extract_audio(video_path: str | Path, out_wav: str | Path) -> Path:
    """Extrahuje audio do 16kHz mono WAV. Vraci cestu k WAV souboru."""
    video_path = Path(video_path)
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        _ffmpeg_bin(),
        "-y",
        "-i", str(video_path),
        "-ac", "1",
        "-ar", "16000",
        "-vn",
        str(out_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    return out_wav
