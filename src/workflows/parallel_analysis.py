"""Parallel workflow: 3 nezavisle analyzatory bezi soubezne (fan-out/fan-in).

Pattern z 5_Claude_Agent_SDK/python/3_workflows/2_parallel_workflow.py.

  scene_detect (code) ──┐
  vad         (code) ──┼──> sjednoceni
  classifier  (LLM)  ──┘
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import anyio

from src.agents.classifier import classify_segments
from src.tools.scene_detect import detect_scenes
from src.tools.vad import detect_speech


async def run_parallel_analysis(
    video_path: Path,
    wav_path: Path,
    transcript: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    """Spusti scene_detect, vad a classifier paralelne. Vraci dict se 3 vystupy."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}

    async def task_scenes() -> None:
        print("  [parallel] scene_detect: start")
        scenes = await anyio.to_thread.run_sync(
            detect_scenes, video_path, out_dir / "scenes.json"
        )
        results["scenes"] = scenes
        print(f"  [parallel] scene_detect: done ({len(scenes)} scenes)")

    async def task_vad() -> None:
        print("  [parallel] vad: start")
        vad = await anyio.to_thread.run_sync(
            detect_speech, wav_path, out_dir / "vad.json"
        )
        results["vad"] = vad
        print(f"  [parallel] vad: done ({len(vad['silence'])} silences)")

    async def task_classifier() -> None:
        print("  [parallel] classifier (LLM): start")
        classified = await classify_segments(transcript["segments"])
        results["classified"] = classified
        print(f"  [parallel] classifier: done ({len(classified)} classifications)")

    async with anyio.create_task_group() as tg:
        tg.start_soon(task_scenes)
        tg.start_soon(task_vad)
        tg.start_soon(task_classifier)

    return results
