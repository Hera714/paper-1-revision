import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from kar3d.knowledge import RouteKnowledgeInjector
from kar3d.config import ExperimentConfig


class MergedKnowledgeTests(unittest.TestCase):
    def test_counts_and_route_isolation(self):
        root=ROOT/'knowledge_packs/merged_routes_v1'
        loader=RouteKnowledgeInjector(root/'rules',root/'rules/route_map.json')
        counts={'line0_pure_vlm':54,'line1_base':56,'line2_orientation':68,'line3_bbox':38}
        self.assertEqual(loader.rule_count,216)
        for route,n in counts.items():
            self.assertEqual(loader.tags_for_route(route),[route])
            self.assertEqual(len(list(loader.iter_route_rules(route))),n)
            self.assertTrue(loader.inject(route))

    def test_every_rule_has_provenance(self):
        root=ROOT/'knowledge_packs/merged_routes_v1'
        manifest=json.loads((root/'manifest.json').read_text())
        for route,stats in manifest['counts'].items():
            sources=manifest['rule_sources'][route]
            self.assertEqual(set(sources),{str(i+1) for i in range(stats['merged_rules'])})
            self.assertTrue(all(sources.values()))
        self.assertEqual(len(manifest['fold_route_audit']),7)

    def test_original_config_preserved_and_new_config_explicit(self):
        old=ExperimentConfig.load(ROOT/'configs/auto_revision_v4.yaml')
        new=ExperimentConfig.load(ROOT/'configs/auto_revision_v4_merged_knowledge_v1.yaml')
        self.assertEqual(old.knowledge_dir,'knowledge')
        self.assertEqual(new.extra['expected_knowledge_rule_count'],216)
        self.assertNotEqual(old.run_name,new.run_name)


if __name__=='__main__':unittest.main()
