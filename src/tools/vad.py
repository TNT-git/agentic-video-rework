"""silero-vad: detekce reci a ticha v audio stope."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def detect_speech(
    wav_path: str | Path,
    out_json: str | Path,
    min_silence_ms: int = 1500,
) -> dict[str, list[dict[str, float]]]:
    """Vraci {speech: [{start,end}], silence: [{start,end,duration}]} v sekundach.

    Silence dlouhe nad min_silence_ms jsou kandidati na SKIP (dlouhe pauzy).
    """
    import soundfile as sf
    import torch
    from silero_vad import load_silero_vad, get_speech_timestamps

    wav_path = Path(wav_path)
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    data, sr = sf.read(str(wav_path), dtype="float32")
    if sr != 16000:
        raise ValueError(f"Ocekavam 16kHz WAV, mam {sr}Hz")
    if data.ndim > 1:
        data = data.mean(axis=1)
    audio = torch.from_numpy(data)

    model = load_silero_vad()
    raw_speech = get_speech_timestamps(
        audio, model, sampling_rate=16000, return_seconds=True
    )

    speech = [{"start": float(s["start"]), "end": float(s["end"])} for s in raw_speech]

    silences: list[dict[str, float]] = []
    if speech:
        if speech[0]["start"] > 0:
            silences.append({
                "start": 0.0,
                "end": speech[0]["start"],
                "duration": speech[0]["start"],
            })
        for prev, nxt in zip(speech, speech[1:]):
            gap = nxt["start"] - prev["end"]
            if gap * 1000 >= min_silence_ms:
                silences.append({
                    "start": prev["end"],
                    "end": nxt["start"],
                    "duration": gap,
                })

    result: dict[str, Any] = {"speech": speech, "silence": silences}
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
