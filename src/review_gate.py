"""Human-in-the-loop review gate: vypise EDL tabulku a ceka na y/n potvrzeni."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

TAG_STYLE = {
    "CORE": "bold green",
    "GENERAL": "green",
    "BONUS": "yellow",
    "SKIP": "red",
}


def show_edl_table(edl: list[dict[str, Any]], transcript_segments: list[dict[str, Any]]) -> None:
    """Vypise EDL jako tabulku s ulomky transkriptu pro kazdy interval."""
    console = Console()
    table = Table(title="Navrh sestrihu (EDL)", show_lines=True)
    table.add_column("#", justify="right", style="cyan", width=3)
    table.add_column("Od", justify="right", width=8)
    table.add_column("Do", justify="right", width=8)
    table.add_column("Trvani", justify="right", width=7)
    table.add_column("Tag", width=8)
    table.add_column("Duvod", width=30)
    table.add_column("Ulomek transkriptu", overflow="fold")

    for i, seg in enumerate(edl, 1):
        snippet = _snippet_for(seg, transcript_segments)
        tag = seg.get("tag", "SKIP").upper()
        style = TAG_STYLE.get(tag, "white")
        table.add_row(
            str(i),
            f"{seg['start']:.2f}",
            f"{seg['end']:.2f}",
            f"{seg['end'] - seg['start']:.2f}",
            f"[{style}]{tag}[/{style}]",
            seg.get("reason", ""),
            snippet[:120],
        )

    console.print(table)


def _snippet_for(
    seg: dict[str, Any],
    transcript_segments: list[dict[str, Any]],
) -> str:
    """Vrati spojeny text z transcript segmentu, ktere spadaji do intervalu seg."""
    parts: list[str] = []
    for ts in transcript_segments:
        if ts["end"] < seg["start"] or ts["start"] > seg["end"]:
            continue
        parts.append(ts["text"])
    return " ".join(parts).strip()


def ask_apply() -> bool:
    """Zepta se uzivatele zda EDL aplikovat. Vraci True/False."""
    answer = input("\nAplikovat tento navrh sestrihu? [y/N]: ").strip().lower()
    return answer in {"y", "yes", "ano", "a"}
