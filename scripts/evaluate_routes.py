#!/usr/bin/env python3
"""Compare saved automatic routes with the original oracle assignments."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kar3d.evaluation import read_jsonl
from kar3d.routing import OracleMetadataRouter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", type=Path)
    args = parser.parse_args()
    rows = read_jsonl(args.predictions)
    oracle = OracleMetadataRouter()
    confusion = Counter()
    matches = 0
    compared = 0
    for row in rows:
        predicted = row.get("routing", {}).get("route")
        if predicted is None:
            continue
        expected = oracle.predict(
            "",
            category=row.get("category", ""),
            sub_category=row.get("sub_category", ""),
        ).route
        confusion[(expected, predicted)] += 1
        matches += int(expected == predicted)
        compared += 1
    report = {
        "compared": compared,
        "matches": matches,
        "agreement": round(100.0 * matches / compared, 4) if compared else 0.0,
        "confusion": [
            {"oracle": key[0], "predicted": key[1], "count": count}
            for key, count in sorted(confusion.items())
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
