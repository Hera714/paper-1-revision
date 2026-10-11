#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
import traceback
from pathlib import Path

from PIL import Image
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kar3d.config import ExperimentConfig
from kar3d.depth import DepthPro3DModule
from kar3d.evaluation import append_jsonl, extract_answer, read_jsonl, summarize
from kar3d.knowledge import RouteKnowledgeInjector
from kar3d.perception import Ovis3DPerceptionModule
from kar3d.pipeline import ThreeDKARPipeline
from kar3d.routing import FixedRouter, OracleMetadataRouter, QuestionOnlyRouter


def parse_args():
    parser = argparse.ArgumentParser(description="Run one reproducible 3D-KAR experiment.")
    parser.add_argument("--config", required=True, help="YAML experiment config")
    return parser.parse_args()


def format_options(item):
    return "\n".join(f"{i}. {item.get(f'Option_{i}', '')}" for i in range(1, 5))


def set_seed(seed: int):
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except Exception:
        pass
    try:
        import torch
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except Exception:
        pass


def main():
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = ExperimentConfig.load(config_path)
    set_seed(config.seed)

    data_path = config.resolve_project_path(PROJECT_ROOT, config.data_path)
    image_dir = Path(config.image_dir)
    output_root = config.resolve_project_path(PROJECT_ROOT, config.output_root)
    run_dir = output_root / config.run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = run_dir / "predictions.jsonl"
    summary_path = run_dir / "summary.json"
    (run_dir / "config.yaml").write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")

    dataset = json.loads(data_path.read_text(encoding="utf-8"))
    end = config.end_index if config.end_index is not None else len(dataset)
    subset = dataset[config.start_index:end]

    perception = Ovis3DPerceptionModule(model_path=config.model_path)
    if config.router_mode == "auto":
        router = QuestionOnlyRouter(
            perception.generate_text,
            confidence_threshold=config.router_confidence_threshold,
        )
    elif config.router_mode == "oracle":
        router = OracleMetadataRouter()
    else:
        router = FixedRouter(config.fixed_route)

    depth = DepthPro3DModule() if config.use_depth else None
    knowledge = None
    if config.use_knowledge:
        knowledge = RouteKnowledgeInjector(
            config.resolve_project_path(PROJECT_ROOT, config.knowledge_dir),
            config.resolve_project_path(PROJECT_ROOT, config.route_map_path),
        )
        if knowledge.rule_count != 74:
            raise RuntimeError(f"Expected 74 knowledge rules, found {knowledge.rule_count}")

    pipeline = ThreeDKARPipeline(
        perception=perception,
        router=router,
        depth=depth,
        knowledge=knowledge,
        use_depth=config.use_depth,
        use_backprojection=config.use_backprojection,
        use_fine_grained_features=config.use_fine_grained_features,
        use_symbolic_relations=config.use_symbolic_relations,
        use_knowledge=config.use_knowledge,
        use_scene_graph_context=config.use_scene_graph_context,
    )

    completed = {str(row["id"]) for row in read_jsonl(predictions_path)}
    for item in tqdm(subset, desc=config.run_name):
        task_id = str(item.get("id"))
        if task_id in completed:
            continue
        record = {
            "id": task_id,
            "image_filename": item.get("Image_Filename"),
            "category": item.get("Category", ""),
            "sub_category": item.get("Sub_Category", ""),
            "answer": str(item.get("Answer", "")),
        }
        try:
            image_path = image_dir / str(item.get("Image_Filename"))
            if not image_path.exists():
                raise FileNotFoundError(str(image_path))
            image = Image.open(image_path).convert("RGB")
            result = pipeline.run(
                image=image,
                question=item["Question"],
                options_text=format_options(item),
                category=item.get("Category") if config.router_mode == "oracle" else None,
                sub_category=item.get("Sub_Category") if config.router_mode == "oracle" else None,
            )
            prediction = extract_answer(result["raw_response"])
            record.update(result)
            record["prediction"] = prediction
            record["is_correct"] = prediction == record["answer"]
            record["status"] = "ok"
        except Exception as exc:
            record.update({
                "prediction": "Error",
                "is_correct": False,
                "status": "error",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            })
        append_jsonl(predictions_path, record)

    records = read_jsonl(predictions_path)
    summary_path.write_text(
        json.dumps(summarize(records), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summarize(records), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
