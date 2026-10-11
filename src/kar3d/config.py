from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class ExperimentConfig:
    run_name: str
    model_path: str = "AIDC-AI/Ovis2.5-9B"
    data_path: str = "data/raw/spatiallab_mcq.json"
    image_dir: str = "/root/autodl-fs/img"
    output_root: str = "outputs"
    knowledge_dir: str = "knowledge"
    route_map_path: str = "knowledge/route_map.json"
    router_mode: str = "auto"
    fixed_route: str = "line1_base"
    router_confidence_threshold: float = 0.55
    start_index: int = 0
    end_index: int | None = None
    seed: int = 42
    use_depth: bool = True
    use_backprojection: bool = True
    use_fine_grained_features: bool = True
    use_symbolic_relations: bool = True
    use_knowledge: bool = True
    use_scene_graph_context: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "ExperimentConfig":
        path = Path(path)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        known = {f.name for f in cls.__dataclass_fields__.values()}
        extra = {k: v for k, v in data.items() if k not in known}
        values = {k: v for k, v in data.items() if k in known}
        values["extra"] = extra
        config = cls(**values)
        if config.router_mode not in {"auto", "oracle", "fixed"}:
            raise ValueError("router_mode must be auto, oracle, or fixed")
        return config

    def resolve_project_path(self, project_root: Path, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else project_root / path
