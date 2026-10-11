from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List


class RouteKnowledgeInjector:
    """Inject the original 74 rules according to the selected processing route."""

    def __init__(self, knowledge_dir: str | Path, route_map_path: str | Path):
        self.knowledge_dir = Path(knowledge_dir)
        self.route_map_path = Path(route_map_path)
        self.rules_by_tag = self._load_rules()
        self.route_map = json.loads(self.route_map_path.read_text(encoding="utf-8"))
        self._validate()

    def _load_rules(self) -> Dict[str, List[str]]:
        rules: Dict[str, List[str]] = {}
        for path in sorted(self.knowledge_dir.glob("*.json")):
            if path.resolve() == self.route_map_path.resolve():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            data.pop("_meta", None)
            for tag, values in data.items():
                if tag in rules:
                    raise ValueError(f"Duplicate knowledge tag: {tag}")
                if not isinstance(values, list):
                    raise ValueError(f"Knowledge entry must be a list: {tag}")
                rules[tag] = [str(v) for v in values]
        return rules

    def _validate(self) -> None:
        missing = {
            tag
            for tags in self.route_map.values()
            for tag in tags
            if tag not in self.rules_by_tag
        }
        if missing:
            raise ValueError(f"Route map references missing knowledge tags: {sorted(missing)}")

    @property
    def rule_count(self) -> int:
        return sum(len(items) for items in self.rules_by_tag.values())

    def tags_for_route(self, route: str) -> List[str]:
        return list(self.route_map.get(route, []))

    def inject(self, route: str) -> str:
        blocks: List[str] = []
        for tag in self.tags_for_route(route):
            rules = self.rules_by_tag[tag]
            if not rules:
                continue
            blocks.append(f"--- Domain Rules ({tag}) ---")
            blocks.extend(f"- {rule}" for rule in rules)
        return "\n".join(blocks)

    def iter_route_rules(self, route: str) -> Iterable[str]:
        for tag in self.tags_for_route(route):
            yield from self.rules_by_tag[tag]
