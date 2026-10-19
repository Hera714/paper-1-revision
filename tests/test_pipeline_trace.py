from kar3d.pipeline import ThreeDKARPipeline
from kar3d.routing import FixedRouter


class FakePerception:
    def generate_text(self, messages, max_tokens, enable_thinking):
        del messages, max_tokens, enable_thinking
        return "<think>Use the image directly.</think><answer>3</answer>"

    def extract_objects_3d(self, image, question, options, task_route):
        del image, question, options, task_route
        return (
            "camera",
            [{"name": "chair", "point_2d": [10, 20], "reason": "Mentioned in question"}],
            '{"objects": [{"name": "chair"}]}',
            {"parse_status": "ok", "objects_accepted": 1},
        )

    def perform_final_reasoning(self, image, question, options, scene_graph, evidence, task_route):
        del image, question, options, scene_graph, evidence, task_route
        return "<think>The chair is nearest.</think>\n1"


def test_pipeline_retains_intermediate_and_final_trace():
    pipeline = ThreeDKARPipeline(
        perception=FakePerception(), router=FixedRouter("line1_base"),
        depth=None, knowledge=None, use_depth=False, use_backprojection=False,
        use_symbolic_relations=False, use_knowledge=False,
    )
    result = pipeline.run(image=None, question="Where is the chair?", options_text="1. Left")

    assert result["selected_route"] == "line1_base"
    assert result["routing"]["route"] == "line1_base"
    assert result["intermediate_trace"]["perception_raw_response"].startswith('{"objects"')
    assert result["intermediate_trace"]["perception_diagnostics"]["parse_status"] == "ok"
    assert result["intermediate_trace"]["object_reasons"] == [
        {"name": "chair", "reason": "Mentioned in question"}
    ]
    assert result["scene_graph"] == result["objects"]
    assert result["final_reasoning_thinking"] == "The chair is nearest."
    assert result["final_answer_text"] == "1"


def test_direct_route_retains_final_trace_without_scene_graph():
    pipeline = ThreeDKARPipeline(
        perception=FakePerception(), router=FixedRouter("line0_pure_vlm"),
        depth=None, knowledge=None, use_depth=False, use_backprojection=False,
        use_symbolic_relations=False, use_knowledge=False,
    )
    result = pipeline.run(image=None, question="What is shown?", options_text="3. Chair")

    assert result["selected_route"] == "line0_pure_vlm"
    assert result["scene_graph"] == []
    assert result["intermediate_trace"]["perception_raw_response"] == ""
    assert result["final_reasoning_thinking"] == "Use the image directly."
    assert result["final_answer_text"] == "<answer>3</answer>"
