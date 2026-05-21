"""Sequential workflow orchestrator: kostra cele pipeline (kroky 1-6).

Pattern z 5_Claude_Agent_SDK/python/3_workflows/1_sequential_workflow.py.

  1. extract_audio       (ffmpeg)
  2. transcribe          (faster-whisper large-v3)
  3. parallel_analysis   (scene + vad + classifier-LLM)  <- Parallel workflow
  4. synthesize          (LLM agent: 3 signaly -> EDL)
  5. review gate         (human-in-the-loop)
  6. conditional_routing + ffmpeg cut  <- Conditional workflow
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

import anyio
from dotenv import load_dotenv

from src.agents.synthesizer import synthesize_edl
from src.review_gate import ask_apply, show_edl_table
from src.tools.cut_video import apply_cuts
from src.tools.extract_audio import extract_audio
from src.tools.transcribe import transcribe_audio
from src.workflows.conditional_routing import route_edl
from src.workflows.parallel_analysis import run_parallel_analysis


def _write_bonus_md(bonus_entries: list[dict[str, Any]], path: Path) -> None:
    lines = ["# BONUS — odbocky mimo hlavni cut\n"]
    for b in bonus_entries:
        lines.append(f"## {b['start']:.2f}s – {b['end']:.2f}s")
        if b.get("reason"):
            lines.append(f"_{b['reason']}_\n")
        if b.get("text"):
            lines.append(b["text"])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


async def run_pipeline(
    video_path: Path,
    out_dir: Path,
    auto_apply: bool = False,
    device: str = "auto",
) -> None:
    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"
    print(f"[init] Whisper device: {device}")
    print("=" * 60)
    print("SEQUENTIAL WORKFLOW: Video-to-EDL pipeline")
    print("=" * 60)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Krok 1: extract audio
    print("\n[1/6] Extrahuji audio (ffmpeg)...")
    wav_path = await anyio.to_thread.run_sync(
        extract_audio, video_path, out_dir / "audio.wav"
    )
    print(f"  -> {wav_path}")

    # --- Krok 2: transkribuj
    print("\n[2/6] Transkribuji (faster-whisper large-v3, CZ)...")
    transcript = await anyio.to_thread.run_sync(
        transcribe_audio,
        wav_path,
        out_dir / "transcript.json",
        "large-v3",
        device,
        "float16" if device == "cuda" else "int8",
    )
    print(f"  -> {len(transcript['segments'])} segmentu, {transcript['duration']:.1f}s")

    # --- Krok 3: parallel analysis (Parallel workflow)
    print("\n[3/6] Paralelni analyza (scene + vad + LLM classifier)...")
    parallel_out = await run_parallel_analysis(
        video_path=video_path,
        wav_path=wav_path,
        transcript=transcript,
        out_dir=out_dir,
    )

    # --- Krok 4: synthesizer agent
    print("\n[4/6] Synthesizer agent (LLM slouci 3 signaly -> EDL)...")
    classified_with_text = [
        {**c, "text": transcript["segments"][c["index"]]["text"]}
        for c in parallel_out["classified"]
        if 0 <= c["index"] < len(transcript["segments"])
    ]
    edl = await synthesize_edl(
        classified_segments=classified_with_text,
        scenes=parallel_out["scenes"],
        silences=parallel_out["vad"]["silence"],
        total_duration=transcript["duration"],
    )
    (out_dir / "edl.json").write_text(
        json.dumps(edl, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  -> EDL ma {len(edl)} segmentu")

    # --- Krok 5: review gate
    print("\n[5/6] Review gate")
    show_edl_table(edl, transcript["segments"])

    if not auto_apply and not ask_apply():
        print("\nZruseno uzivatelem. EDL ulozeno v edl.json, video nesestrizeno.")
        return

    # --- Krok 6: conditional routing + ffmpeg cut (Conditional workflow)
    print("\n[6/6] Conditional routing (per-segment) + ffmpeg sestrih...")
    buckets = route_edl(edl)
    print(
        f"  routing: keep={len(buckets['keep'])} "
        f"bonus={len(buckets['bonus'])} "
        f"skip={len(buckets['skip'])}"
    )

    if buckets["bonus"]:
        bonus_path = out_dir / "bonus.md"
        _write_bonus_md(buckets["bonus"], bonus_path)
        print(f"  -> {bonus_path}")

    if not buckets["keep"]:
        print("  POZOR: zadne CORE/GENERAL segmenty — video by bylo prazdne. Konec.")
        return

    cut_path = await anyio.to_thread.run_sync(
        apply_cuts, video_path, buckets["keep"], out_dir / "cut.mp4"
    )
    print(f"  -> {cut_path}")

    print("\n" + "=" * 60)
    print("HOTOVO.")
    print("=" * 60)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Video-to-EDL pipeline.")
    parser.add_argument("video", type=Path, help="Cesta k MP4")
    parser.add_argument(
        "--out", type=Path, default=None, help="Vystupni adresar (default data/output/<jmeno>)"
    )
    parser.add_argument(
        "--device", default="auto", choices=["auto", "cuda", "cpu"], help="Whisper device (auto detekuje)"
    )
    parser.add_argument(
        "--auto-apply", action="store_true", help="Bez review gate, rovnou sestrihne"
    )
    args = parser.parse_args()

    if not args.video.exists():
        print(f"Video neexistuje: {args.video}", file=sys.stderr)
        return 1

    out_dir = args.out or (Path("data/output") / args.video.stem)

    anyio.run(run_pipeline, args.video, out_dir, args.auto_apply, args.device)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
