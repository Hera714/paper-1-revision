#!/usr/bin/env python3
"""Run the question-only controller without images, depth, or final reasoning."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kar3d.config import ExperimentConfig
from kar3d.evaluation import append_jsonl, read_jsonl
from kar3d.perception import Ovis3DPerceptionModule
from kar3d.routing import QuestionOnlyRouter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = ExperimentConfig.load(args.config)
    if config.router_mode != "auto":
        raise ValueError("Route-only prediction requires router_mode: auto")

    data_path = config.resolve_project_path(PROJECT_ROOT, config.data_path)
    output_root = config.resolve_project_path(PROJECT_ROOT, config.output_root)
    run_dir = output_root / config.run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / "routes.jsonl"
    summary_path = run_dir / "routes_summary.json"

    dataset = json.loads(data_path.read_text(encoding="utf-8"))
    end = config.end_index if config.end_index is not None else len(dataset)
    subset = dataset[config.start_index:end]
    completed = {str(row["id"]) for row in read_jsonl(output_path)}

    model_path = Path(config.model_path)
    if model_path.is_absolute() and not model_path.is_dir():
        raise FileNotFoundError(f"Ovis model directory not found: {model_path}")
    perception = Ovis3DPerceptionModule(model_path=config.model_path)
    router = QuestionOnlyRouter(
        perception.generate_text,
        confidence_threshold=config.router_confidence_threshold,
    )
    for item in tqdm(subset, desc="question-only routing"):
        task_id = str(item.get("id"))
        if task_id in completed:
            continue
        decision = router.predict(item["Question"])
        append_jsonl(output_path, {
            "id": task_id,
            "category": item.get("Category", ""),
            "sub_category": item.get("Sub_Category", ""),
            "routing": decision.to_dict(),
        })

    rows = read_jsonl(output_path)
    counts = Counter(row["routing"]["route"] for row in rows)
    confidences = [float(row["routing"]["confidence"]) for row in rows]
    fallback_count = sum(
        row["routing"].get("proposed_route") != row["routing"].get("route")
        for row in rows
    )
    summary = {
        "evaluated": len(rows),
        "route_counts": dict(sorted(counts.items())),
        "mean_confidence": round(statistics.mean(confidences), 4) if confidences else 0.0,
        "median_confidence": round(statistics.median(confidences), 4) if confidences else 0.0,
        "low_confidence_fallbacks": fallback_count,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
