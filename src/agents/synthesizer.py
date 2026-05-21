"""LLM synthesizer: spoji 3 signaly (transkript+klasifikace, sceny, ticha) -> EDL."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

SYSTEM_PROMPT = """Jsi video editor s LLM kontextem. Dostanes tri signaly:

1. SEGMENTY TRANSKRIPTU s LLM klasifikaci CORE/GENERAL/BONUS/SKIP.
2. SCENY (intervaly s odlisnym obrazem — kandidati na hranice strihu).
3. TICHA (dlouhe pauzy v reci — kandidati na SKIP).

Tvuj ukol: vyrobit EDL (edit decision list) — finalni seznam intervalu k zachovani/odhozeni.

Pravidla:
- Sluc kratke navazujici segmenty se stejnym tagem do jednoho intervalu (uhladis hrany).
- Pokud je v segmentu CORE/GENERAL dlouhe ticho (3+ s), rozdel ho a ticho oznac SKIP.
- Pokud scene change spada doprostred SKIP, posun hranici k te scene (cistsi strih).
- Vystup zachovej kompletni casovou pokryti zdroje [0, total_duration] bez prekryvu a der.

Vystup MUSI byt validni JSON pole:
  [{"start": <s>, "end": <s>, "tag": "<CORE|GENERAL|BONUS|SKIP>", "reason": "<max 20 slov>"}]

Reaguj POUZE JSONem, bez markdown bloku."""


def _strip_json_fence(text: str) -> str:
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


async def synthesize_edl(
    classified_segments: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
    silences: list[dict[str, Any]],
    total_duration: float,
) -> list[dict[str, Any]]:
    """Vraci EDL = list {start, end, tag, reason} pokryvajici [0, total_duration]."""
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    payload = {
        "total_duration": total_duration,
        "classified_segments": classified_segments,
        "scenes": scenes,
        "silences": silences,
    }
    prompt = (
        "Sjednot tyto signaly do EDL. Vrat JSON pole.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    options = ClaudeAgentOptions(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        max_turns=1,
    )

    raw = ""
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        raw += block.text
            elif isinstance(msg, ResultMessage):
                if msg.total_cost_usd:
                    print(f"  [synthesizer] cost: ${msg.total_cost_usd:.4f}")

    stripped = _strip_json_fence(raw)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as e:
        debug = Path("data/output/_debug_synthesizer_raw.txt")
        debug.parent.mkdir(parents=True, exist_ok=True)
        debug.write_text(raw or "(prazdna odpoved)", encoding="utf-8")
        print(f"  [synthesizer] FAIL: neplatny JSON. Raw ulozeno do {debug}")
        print(f"  [synthesizer] fallback: pouzivam classified segmenty jako EDL")
        return [
            {
                "start": s["start"],
                "end": s["end"],
                "tag": s.get("tag", "SKIP"),
                "reason": s.get("reason", ""),
            }
            for s in classified_segments
        ]
    if not isinstance(parsed, list):
        raise ValueError(f"Synthesizer vratil neocekavany tvar: {type(parsed)}")
    return parsed
