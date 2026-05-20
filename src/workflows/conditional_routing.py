"""Conditional workflow: per-segment IF/ELSE routing podle tagu.

Pattern z 5_Claude_Agent_SDK/python/3_workflows/3_conditional_workflow.py.

  CORE     ──> keep
  GENERAL  ──> keep
  BONUS    ──> bonus.md (text), nezachovat ve videu
  SKIP     ──> cut

Vystupem je rozdeleni segmentu do 3 listu: keep_intervals, bonus_entries, skip_intervals.
"""

from __future__ import annotations

from typing import Any, Callable


def _route_keep(seg: dict[str, Any]) -> dict[str, Any]:
    return {"start": seg["start"], "end": seg["end"]}


def _route_bonus(seg: dict[str, Any]) -> dict[str, Any]:
    return {
        "start": seg["start"],
        "end": seg["end"],
        "reason": seg.get("reason", ""),
        "text": seg.get("text", ""),
    }


def _route_skip(seg: dict[str, Any]) -> dict[str, Any]:
    return {
        "start": seg["start"],
        "end": seg["end"],
        "reason": seg.get("reason", ""),
    }


ROUTING_TABLE: dict[str, tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]] = {
    "CORE":    ("keep",  _route_keep),
    "GENERAL": ("keep",  _route_keep),
    "BONUS":   ("bonus", _route_bonus),
    "SKIP":    ("skip",  _route_skip),
}


def route_edl(edl: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Routuje kazdy EDL segment do 1 ze 3 vystupnich kos podle tagu."""
    buckets: dict[str, list[dict[str, Any]]] = {"keep": [], "bonus": [], "skip": []}

    for seg in edl:
        tag = seg.get("tag", "SKIP").upper()
        bucket, fn = ROUTING_TABLE.get(tag, ROUTING_TABLE["SKIP"])
        buckets[bucket].append(fn(seg))

    buckets["keep"].sort(key=lambda x: x["start"])
    return buckets
