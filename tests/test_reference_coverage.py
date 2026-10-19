import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kar3d.pipeline import ThreeDKARPipeline
from kar3d.reference_coverage import (
    missing_references,
    non_entity_object_names,
    question_references,
)


class ReferenceCoverageTests(unittest.TestCase):
    def test_explicit_references_only(self):
        question = "What is between the overcoat and the mirror?"
        self.assertEqual([ref.name for ref in question_references(question)], ["overcoat", "mirror"])
        self.assertEqual([ref.name for ref in missing_references(question, [{"name": "Mirror"}])],
                         ["overcoat"])

    def test_multiple_reference_patterns(self):
        self.assertEqual([ref.name for ref in question_references(
            "Which item could fit inside the rattan basket near the ladder?")],
            ["rattan basket", "ladder"])
        self.assertEqual([ref.name for ref in question_references(
            "Which group is further away from the open doorway?")], ["open doorway"])

    def test_abstract_image_position_is_not_entity(self):
        self.assertEqual(question_references("Which cup is closest to the center of the image?"), [])
        self.assertEqual(non_entity_object_names([{"name": "Nothing"}, {"name": "Mirror"}]),
                         ["Nothing"])


class _Router:
    def predict(self, question):
        return _Decision()


class _Decision:
    route = "line1_base"
    reason = "test"
    raw_response = "<answer>line1_base</answer>"

    def to_dict(self):
        return {"route": self.route, "reason": self.reason}


class _Perception:
    def __init__(self, repair_point=(40, 40)):
        self.calls = 0
        self.repair_point = repair_point

    def extract_objects_3d(self, image, question, options, task_route):
        self.calls += 1
        if self.calls == 1:
            return "camera", [{"name": "bench", "point_2d": [100, 100]}], "first", {}
        return "camera", [
            {"name": "overcoat", "point_2d": list(self.repair_point)},
            {"name": "mirror", "point_2d": [200, 200]},
            {"name": "Nothing", "point_2d": [300, 300]},
        ], "second", {}

    def perform_final_reasoning(self, image, question, options, graph, evidence, task_route):
        return "<think>test</think><answer>1</answer>"


def _run(mode, repair_point=(40, 40)):
    perception = _Perception(repair_point)
    pipeline = ThreeDKARPipeline(
        perception=perception, router=_Router(), depth=None, knowledge=None,
        use_depth=False, use_backprojection=False, use_symbolic_relations=False,
        use_knowledge=False, reference_coverage_mode=mode,
    )
    result = pipeline.run(image=SimpleNamespace(width=600, height=600),
                          question="What is between the overcoat and the mirror?",
                          options_text="1. bench\n2. Nothing\n3. table\n4. chair")
    return result, perception.calls


class PipelineRepairTests(unittest.TestCase):
    def test_off_preserves_original_behavior(self):
        result, calls = _run("off")
        self.assertEqual(calls, 1)
        self.assertEqual([obj["name"] for obj in result["scene_graph"]], ["bench"])
        self.assertNotIn("reference_coverage", result["intermediate_trace"])

    def test_audit_does_not_reextract(self):
        result, calls = _run("audit")
        self.assertEqual(calls, 1)
        self.assertEqual([obj["name"] for obj in result["scene_graph"]], ["bench"])
        self.assertEqual(result["intermediate_trace"]["reference_coverage"]["missing_before"],
                         ["overcoat", "mirror"])

    def test_repair_adds_only_valid_missing_objects(self):
        result, calls = _run("repair")
        self.assertEqual(calls, 2)
        self.assertEqual([obj["name"] for obj in result["scene_graph"]],
                         ["bench", "overcoat", "mirror"])
        trace = result["intermediate_trace"]["reference_coverage"]
        self.assertTrue(trace["repair_attempted"])
        self.assertEqual(trace["added_names"], ["overcoat", "mirror"])
        self.assertEqual(trace["missing_after"], [])

    def test_repair_rejects_out_of_bounds_point(self):
        result, _ = _run("repair", repair_point=(700, 40))
        self.assertEqual([obj["name"] for obj in result["scene_graph"]], ["bench", "mirror"])
        self.assertEqual(result["intermediate_trace"]["reference_coverage"]["missing_after"],
                         ["overcoat"])


if __name__ == "__main__":
    unittest.main()
