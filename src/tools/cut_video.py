"""ffmpeg sestrih videa podle EDL (zachovat jen intervaly oznacene 'keep')."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _ffmpeg_bin() -> str:
    return os.environ.get("FFMPEG_PATH", "ffmpeg")


def apply_cuts(
    video_path: str | Path,
    keep_intervals: list[dict[str, float]],
    out_video: str | Path,
) -> Path:
    """Sestrihne video podle keep_intervals=[{start,end}] -> out_video.

    Pouziva ffmpeg concat demuxer s re-encode (jednoduche a spolehlive na sample).
    """
    video_path = Path(video_path)
    out_video = Path(out_video)
    out_video.parent.mkdir(parents=True, exist_ok=True)

    if not keep_intervals:
        raise ValueError("No keep intervals — nothing to output.")

    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        parts: list[Path] = []
        for i, iv in enumerate(keep_intervals):
            part = tmp / f"part_{i:03d}.mp4"
            cmd = [
                _ffmpeg_bin(), "-y",
                "-ss", f"{iv['start']:.3f}",
                "-to", f"{iv['end']:.3f}",
                "-i", str(video_path),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                str(part),
            ]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"ffmpeg part {i} failed: {r.stderr[-500:]}")
            parts.append(part)

        list_file = tmp / "concat.txt"
        list_file.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in parts),
            encoding="utf-8",
        )
        cmd = [
            _ffmpeg_bin(), "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(out_video),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {r.stderr[-500:]}")

    return out_video
