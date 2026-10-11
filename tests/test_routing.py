import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kar3d.routing import OracleMetadataRouter, QuestionOnlyRouter


class RoutingTests(unittest.TestCase):
    def test_valid_controller_json(self):
        parsed = QuestionOnlyRouter.parse_response(
            '{"route":"line3_bbox","confidence":0.83,"reason":"Needs extent."}'
        )
        self.assertEqual(parsed["route"], "line3_bbox")
        self.assertEqual(parsed["confidence"], 0.83)

    def test_invalid_controller_json_falls_back(self):
        parsed = QuestionOnlyRouter.parse_response("not json")
        self.assertEqual(parsed["route"], "line1_base")
        self.assertEqual(parsed["confidence"], 0.0)

    def test_low_confidence_falls_back_to_basic(self):
        def fake_generator(messages, max_tokens, enable_thinking):
            del messages, max_tokens, enable_thinking
            return '{"route":"line2_orientation","confidence":0.3,"reason":"uncertain"}'

        decision = QuestionOnlyRouter(fake_generator, confidence_threshold=0.55).predict("Question")
        self.assertEqual(decision.proposed_route, "line2_orientation")
        self.assertEqual(decision.route, "line1_base")

    def test_original_oracle_precedence(self):
        router = OracleMetadataRouter()
        decision = router.predict(
            "",
            category="Size & Scale",
            sub_category="Scale Consistency",
        )
        self.assertEqual(decision.route, "line0_pure_vlm")


if __name__ == "__main__":
    unittest.main()
