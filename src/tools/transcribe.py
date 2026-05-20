"""faster-whisper large-v3 CZ transkripce s word-level timestamps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

INITIAL_PROMPT = (
    "Skoleni o AI vyvoji. Termíny: Claude, Claude Code, Anthropic, "
    "Codex, OpenAI, GitHub, repozitář, commit, pull request, branch, "
    "MCP server, SDK, API, agent, subagent, skill, hook, workflow, "
    "Python, TypeScript, NinjaTrader, NinjaScript, indikátor."
)


def transcribe_audio(
    wav_path: str | Path,
    out_json: str | Path,
    model_size: str = "large-v3",
    device: str = "cuda",
    compute_type: str = "float16",
) -> dict[str, Any]:
    """Transkripce CZ audia. Vraci dict {language, segments[{start,end,text,words[{start,end,word}]}]}."""
    from faster_whisper import WhisperModel

    wav_path = Path(wav_path)
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    segments_gen, info = model.transcribe(
        str(wav_path),
        language="cs",
        word_timestamps=True,
        initial_prompt=INITIAL_PROMPT,
        vad_filter=False,
    )

    segments: list[dict[str, Any]] = []
    for seg in segments_gen:
        words = [
            {"start": w.start, "end": w.end, "word": w.word}
            for w in (seg.words or [])
        ]
        segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
            "words": words,
        })

    result = {
        "language": info.language,
        "duration": info.duration,
        "segments": segments,
    }
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
