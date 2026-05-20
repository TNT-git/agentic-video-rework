"""End-to-end demo: spusti pipeline na data/samples/sample_30s.mp4.

Pouziti:
    python examples/run_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import anyio
from dotenv import load_dotenv

from src.pipeline import run_pipeline


def main() -> int:
    load_dotenv()
    sample = REPO_ROOT / "data" / "samples" / "sample_30s.mp4"
    if not sample.exists():
        print(f"Sample chybi: {sample}")
        print("Vytvor sample napr. ffmpegem:")
        print('  ffmpeg -ss 60 -t 30 -i "data/input/lekce5.mp4" -c copy data/samples/sample_30s.mp4')
        return 1

    out_dir = REPO_ROOT / "data" / "output" / sample.stem
    anyio.run(run_pipeline, sample, out_dir, False, "cuda")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
