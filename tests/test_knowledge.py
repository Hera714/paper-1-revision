import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kar3d.knowledge import RouteKnowledgeInjector
from kar3d.routing import ROUTES


class KnowledgeTests(unittest.TestCase):
    def test_all_74_rules_are_loaded_and_mapped(self):
        injector = RouteKnowledgeInjector(ROOT / "knowledge", ROOT / "knowledge" / "route_map.json")
        self.assertEqual(injector.rule_count, 74)
        mapped = set()
        for route in ROUTES:
            mapped.update(injector.tags_for_route(route))
            self.assertTrue(injector.inject(route))
        self.assertEqual(mapped, set(injector.rules_by_tag))


if __name__ == "__main__":
    unittest.main()
