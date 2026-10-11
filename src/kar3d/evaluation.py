from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


def extract_answer(response: str) -> str:
    if not response:
        return "Unknown"
    tagged = re.search(r"<answer>\s*([1-4])\s*</answer>", response)
    if tagged:
        return tagged.group(1)
    return "Unknown"


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def summarize(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(records)
    correct = sum(bool(row.get("is_correct")) for row in rows)
    route_counts = Counter(row.get("routing", {}).get("route", "unknown") for row in rows)
    category_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    for row in rows:
        category = row.get("category", "Unknown")
        category_stats[category]["total"] += 1
        category_stats[category]["correct"] += int(bool(row.get("is_correct")))
    by_category = {}
    for category, stats in sorted(category_stats.items()):
        total = stats["total"]
        by_category[category] = {
            **stats,
            "accuracy": round(100.0 * stats["correct"] / total, 4) if total else 0.0,
        }
    return {
        "evaluated": len(rows),
        "correct": correct,
        "accuracy": round(100.0 * correct / len(rows), 4) if rows else 0.0,
        "route_counts": dict(sorted(route_counts.items())),
        "by_category": by_category,
    }
