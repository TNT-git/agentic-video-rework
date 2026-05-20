"""PySceneDetect: detekce zmen obrazu (prepnuti slidu, prepnuti do IDE...)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def detect_scenes(
    video_path: str | Path,
    out_json: str | Path,
    threshold: float = 27.0,
) -> list[dict[str, Any]]:
    """Vraci list scen [{start, end, duration}] v sekundach."""
    from scenedetect import detect, ContentDetector

    video_path = Path(video_path)
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    scene_list = detect(str(video_path), ContentDetector(threshold=threshold))

    scenes = [
        {
            "start": s.get_seconds(),
            "end": e.get_seconds(),
            "duration": e.get_seconds() - s.get_seconds(),
        }
        for s, e in scene_list
    ]
    out_json.write_text(json.dumps(scenes, indent=2), encoding="utf-8")
    return scenes
