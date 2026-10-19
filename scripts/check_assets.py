#!/usr/bin/env python3
"""Check local model weights, benchmark data, and images without loading a model."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kar3d.config import ExperimentConfig


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = ExperimentConfig.load(args.config)

    problems = []
    model_dir = Path(config.model_path)
    if not model_dir.is_dir():
        problems.append(f"Ovis model directory missing: {model_dir}")
    else:
        index_path = model_dir / "model.safetensors.index.json"
        if not index_path.is_file():
            problems.append(f"Ovis weight index missing: {index_path}")
        else:
            weight_map = json.loads(index_path.read_text(encoding="utf-8"))["weight_map"]
            shards = sorted(set(weight_map.values()))
            missing_shards = [name for name in shards if not (model_dir / name).is_file()]
            empty_shards = [name for name in shards if (model_dir / name).is_file() and (model_dir / name).stat().st_size == 0]
            print(f"Ovis model: {model_dir} ({len(shards)} weight shards)")
            if missing_shards:
                problems.append(f"Missing Ovis weight shards: {missing_shards}")
            if empty_shards:
                problems.append(f"Empty Ovis weight shards: {empty_shards}")

    if config.use_depth:
        checkpoint = config.resolve_project_path(PROJECT_ROOT, config.depth_checkpoint_path)
        if not checkpoint.is_file() or checkpoint.stat().st_size == 0:
            problems.append(f"Depth Pro checkpoint missing or empty: {checkpoint}")
        else:
            print(f"Depth Pro checkpoint: {checkpoint} ({checkpoint.stat().st_size} bytes)")

    data_path = config.resolve_project_path(PROJECT_ROOT, config.data_path)
    image_dir = config.resolve_project_path(PROJECT_ROOT, config.image_dir)
    if not data_path.is_file():
        problems.append(f"Dataset missing: {data_path}")
    elif not image_dir.is_dir():
        problems.append(f"Image directory missing: {image_dir}")
    else:
        raw_data = data_path.read_bytes()
        dataset = json.loads(raw_data)
        missing_images = [
            row.get("Image_Filename")
            for row in dataset
            if not (image_dir / str(row.get("Image_Filename"))).is_file()
        ]
        print(f"Dataset: {data_path} ({len(dataset)} records)")
        print(f"Images: {image_dir} ({len(dataset) - len(missing_images)}/{len(dataset)} matched)")
        if missing_images:
            problems.append(f"Missing images, first five: {missing_images[:5]}")

        manifest_path = PROJECT_ROOT / "data" / "manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if len(dataset) != manifest.get("records"):
                problems.append("Dataset record count differs from data/manifest.json")
            if hashlib.sha256(raw_data).hexdigest() != manifest.get("json_sha256"):
                problems.append("Dataset checksum differs from data/manifest.json")

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1
    print("All configured local assets are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
