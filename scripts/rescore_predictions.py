#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kar3d.evaluation import extract_answer, read_jsonl, summarize


def parse_args():
    parser = argparse.ArgumentParser(
        description="Re-parse saved model responses without rerunning inference."
    )
    parser.add_argument("input", help="Existing predictions.jsonl")
    parser.add_argument(
        "--output",
        help="New JSONL path (default: predictions_rescored.jsonl beside input)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input).resolve()
    output_path = (
        Path(args.output).resolve()
        if args.output
        else input_path.with_name("predictions_rescored.jsonl")
    )
    if output_path == input_path:
        raise ValueError("Refusing to overwrite the original predictions file.")

    rows = read_jsonl(input_path)
    rescored = []
    changed_predictions = 0
    recovered_unknown = 0
    changed_correctness = 0
    for original in rows:
        row = dict(original)
        old_prediction = str(row.get("prediction", "Unknown"))
        old_correct = bool(row.get("is_correct"))
        new_prediction = (
            extract_answer(str(row.get("raw_response", "")))
            if row.get("status") == "ok"
            else old_prediction
        )
        new_correct = new_prediction == str(row.get("answer", ""))
        row["original_prediction"] = old_prediction
        row["original_is_correct"] = old_correct
        row["prediction"] = new_prediction
        row["is_correct"] = new_correct
        changed_predictions += int(new_prediction != old_prediction)
        recovered_unknown += int(old_prediction == "Unknown" and new_prediction != "Unknown")
        changed_correctness += int(new_correct != old_correct)
        rescored.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rescored:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    result = summarize(rescored)
    result["source_predictions"] = str(input_path)
    result["rescored_predictions"] = str(output_path)
    result["changed_predictions"] = changed_predictions
    result["recovered_unknown"] = recovered_unknown
    result["changed_correctness"] = changed_correctness
    summary_path = output_path.with_name("summary_rescored.json")
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
