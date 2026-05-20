"""LLM klasifikator: rozhodne pro kazdy segment transkriptu tag CORE/GENERAL/BONUS/SKIP."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

SYSTEM_PROMPT = """Jsi klasifikator transkriptu z videa AI/programatorskeho skoleni.

Tvuj ukol: kazdou polozku ve vstupu oznacit jednim ze 4 tagu:

- CORE     — primo k tematu lekce, klicove vysvetleni, prakticky postup, definice.
- GENERAL  — princip plati siroce i mimo lekci (system prompts, agent loops, context engineering...). Stoji za zachovani.
- BONUS    — zajimava odbocka / Q&A mimo hlavni tema, ale ma hodnotu. Ulozi se do BONUS souboru, ne do hlavniho cutu.
- SKIP     — balast: dlouhe pauzy, "pockejte kde jsem to mel", technicke problemy ("nejede mi to"), off-topic studentske vstupy, opakovani uvodu.

Vstup dostanes jako JSON pole segmentu se start/end/text. Vystup MUSI byt validni JSON pole STEJNE delky, kde kazdy prvek je:
  {"index": <int>, "tag": "<CORE|GENERAL|BONUS|SKIP>", "reason": "<kratke odvodneni, max 20 slov>"}

Reaguj POUZE JSONem, bez markdown bloku, bez komentaru. Vytvor jeden zaznam pro kazdy vstupni segment, zachovej poradi."""


def _strip_json_fence(text: str) -> str:
    """Odstrani pripadny ```json ... ``` wrapper okolo JSON."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


async def classify_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Klasifikuje seznam segmentu transkriptu. Vraci list {index, tag, reason}."""
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    compact_in = [
        {"index": i, "start": s["start"], "end": s["end"], "text": s["text"]}
        for i, s in enumerate(segments)
    ]
    prompt = (
        "Klasifikuj nasledujici segmenty transkriptu. Vrat JSON pole stejne delky.\n\n"
        f"Segmenty:\n{json.dumps(compact_in, ensure_ascii=False, indent=2)}"
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
                    print(f"  [classifier] cost: ${msg.total_cost_usd:.4f}")

    parsed = json.loads(_strip_json_fence(raw))
    if not isinstance(parsed, list):
        raise ValueError(f"Classifier vratil neocekavany tvar: {type(parsed)}")
    return parsed
