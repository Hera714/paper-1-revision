from __future__ import annotations

import math
import time
from typing import Any, Dict, Optional

from .evaluation import split_thinking_and_answer
from .reference_coverage import (
    is_non_entity_name,
    missing_references,
    non_entity_object_names,
    reference_present,
)
from .relations_bbox import generate_bbox_relations
from .relations_pose import generate_spatial_relations


class ThreeDKARPipeline:
    """One canonical implementation for the full method and its ablations."""

    def __init__(
        self,
        *,
        perception: Any,
        router: Any,
        depth: Optional[Any],
        knowledge: Optional[Any],
        use_depth: bool = True,
        use_backprojection: bool = True,
        use_fine_grained_features: bool = True,
        use_symbolic_relations: bool = True,
        use_knowledge: bool = True,
        use_scene_graph_context: bool = True,
        reference_coverage_mode: str = "off",
    ):
        self.perception = perception
        self.router = router
        self.depth = depth
        self.knowledge = knowledge
        self.use_depth = use_depth
        self.use_backprojection = use_backprojection
        self.use_fine_grained_features = use_fine_grained_features
        self.use_symbolic_relations = use_symbolic_relations
        self.use_knowledge = use_knowledge
        self.use_scene_graph_context = use_scene_graph_context
        if reference_coverage_mode not in {"off", "audit", "repair"}:
            raise ValueError("reference_coverage_mode must be off, audit, or repair")
        self.reference_coverage_mode = reference_coverage_mode
        if self.use_backprojection and not self.use_depth:
            raise ValueError("3D back-projection requires depth estimation.")
        if self.use_depth and self.depth is None:
            raise ValueError("A depth module is required when use_depth=true.")

    @staticmethod
    def _time_since(start: float) -> float:
        return round(time.perf_counter() - start, 4)

    def _route(self, question: str, category: Optional[str], sub_category: Optional[str]):
        if getattr(self.router, "__class__", None).__name__ == "OracleMetadataRouter":
            return self.router.predict(
                question,
                category=category or "",
                sub_category=sub_category or "",
            )
        return self.router.predict(question)

    def _knowledge_text(self, route: str) -> str:
        if not self.use_knowledge or self.knowledge is None:
            return ""
        return self.knowledge.inject(route)

    @staticmethod
    def _trace_fields(decision, perception_raw_response: str, scene_graph: list,
                      spatial_relations_text: str, final_response: str,
                      perception_diagnostics: Optional[Dict[str, Any]] = None,
                      reference_coverage: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        routing_thinking, _ = split_thinking_and_answer(decision.raw_response)
        perception_thinking, _ = split_thinking_and_answer(perception_raw_response)
        final_thinking, final_answer_text = split_thinking_and_answer(final_response)
        trace = {
            "selected_route": decision.route,
            "intermediate_trace": {
                "routing_thinking": routing_thinking,
                "routing_reason": decision.reason,
                "perception_raw_response": perception_raw_response,
                "perception_thinking": perception_thinking,
                "perception_diagnostics": perception_diagnostics or {},
                "object_reasons": [
                    {"name": obj.get("name", "Unknown"), "reason": obj.get("reason", "")}
                    for obj in scene_graph
                ],
                "spatial_relations_text": spatial_relations_text,
            },
            "scene_graph": scene_graph,
            "final_reasoning_thinking": final_thinking,
            "final_answer_text": final_answer_text,
        }
        if reference_coverage is not None:
            trace["intermediate_trace"]["reference_coverage"] = reference_coverage
        return trace

    @staticmethod
    def _valid_repair_object(obj: Dict[str, Any], image, route: str) -> bool:
        name = str(obj.get("name", "")).strip()
        point = obj.get("point_2d")
        if not name or is_non_entity_name(name) or not isinstance(point, (list, tuple)) or len(point) != 2:
            return False
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v)
               for v in point):
            return False
        if not (0 <= point[0] < image.width and 0 <= point[1] < image.height):
            return False
        reason = str(obj.get("reason", "")).casefold()
        if any(word in reason for word in ("not visible", "not found", "absent", "cannot see", "can't see")):
            return False
        if route == "line3_bbox":
            box = obj.get("bbox_2d")
            if not isinstance(box, (list, tuple)) or len(box) != 4:
                return False
            if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v)
                   for v in box):
                return False
            x0, y0, x1, y1 = box
            if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
                return False
            if not (x0 <= point[0] <= x1 and y0 <= point[1] <= y1):
                return False
        return True

    def _direct_reasoning(self, image, question: str, options_text: str, knowledge_text: str) -> str:
        prompt = (
            "Answer the question directly based on the image.\n"
            "Output a <think> block for step-by-step reasoning, then your exact "
            "answer as a single number (1-4) inside <answer> tags."
        )
        if knowledge_text:
            prompt += "\n\n--- EXTERNAL DOMAIN KNOWLEDGE ---\n" + knowledge_text
        prompt += f"\n\nQuestion:\n{question}\nOptions:\n{options_text}\nAnswer (1-4):"
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }]
        return self.perception.generate_text(messages, max_tokens=2048, enable_thinking=True)

    def run(
        self,
        *,
        image,
        question: str,
        options_text: str,
        category: Optional[str] = None,
        sub_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        timings: Dict[str, float] = {}
        total_start = time.perf_counter()

        started = time.perf_counter()
        decision = self._route(question, category, sub_category)
        timings["routing_seconds"] = self._time_since(started)
        route = decision.route

        knowledge_text = self._knowledge_text(route)
        if route == "line0_pure_vlm":
            started = time.perf_counter()
            response = self._direct_reasoning(image, question, options_text, knowledge_text)
            timings["final_reasoning_seconds"] = self._time_since(started)
            timings["total_seconds"] = self._time_since(total_start)
            return {
                "routing": decision.to_dict(),
                **self._trace_fields(decision, "", [], "", response),
                "target_perspective": "camera",
                "objects": [],
                "spatial_relations_text": "",
                "knowledge_text": knowledge_text,
                "raw_response": response,
                "timings": timings,
            }

        extraction_route = route if self.use_fine_grained_features else "line1_base"
        started = time.perf_counter()
        extraction_result = self.perception.extract_objects_3d(
            image,
            question,
            options_text,
            task_route=extraction_route,
        )
        if len(extraction_result) == 4:
            target_perspective, objects_data, perception_raw_response, perception_diagnostics = extraction_result
        else:
            target_perspective, objects_data, perception_raw_response = extraction_result
            perception_diagnostics = {}
        timings["perception_seconds"] = self._time_since(started)

        reference_coverage = None
        if self.reference_coverage_mode != "off":
            non_entities = non_entity_object_names(objects_data)
            if self.reference_coverage_mode == "repair":
                objects_data = [obj for obj in objects_data
                                if not is_non_entity_name(str(obj.get("name", "")))]
            missing = missing_references(question, objects_data)
            reference_coverage = {
                "mode": self.reference_coverage_mode,
                "missing_before": [ref.name for ref in missing],
                "non_entity_names": non_entities,
                "repair_attempted": False,
                "added_names": [],
            }
            if self.reference_coverage_mode == "repair" and missing:
                started = time.perf_counter()
                repair_question = (
                    question + "\n\nScene-graph extraction clarification: The question explicitly "
                    "mentions these reference objects: " + ", ".join(ref.name for ref in missing)
                    + ". If visibly present, include each as a separate object with a point "
                    "inside it; do not invent absent objects. Keep the original question "
                    "and answer options unchanged."
                )
                retry = self.perception.extract_objects_3d(
                    image, repair_question, options_text, task_route=extraction_route
                )
                retry_perspective, candidates, retry_raw = retry[:3]
                reference_coverage["repair_attempted"] = True
                reference_coverage["repair_raw_response"] = retry_raw
                reference_coverage["repair_target_perspective"] = retry_perspective
                if len(retry) == 4:
                    reference_coverage["repair_diagnostics"] = retry[3]
                for candidate in candidates:
                    if not self._valid_repair_object(candidate, image, extraction_route):
                        continue
                    if not any(reference_present(ref, [candidate]) for ref in missing):
                        continue
                    if any(str(candidate["name"]).casefold() == str(obj.get("name", "")).casefold()
                           for obj in objects_data):
                        continue
                    px, py = candidate["point_2d"]
                    if any(math.hypot(px - obj["point_2d"][0], py - obj["point_2d"][1]) < 3
                           for obj in objects_data if isinstance(obj.get("point_2d"), (list, tuple))
                           and len(obj["point_2d"]) == 2):
                        continue
                    objects_data.append(candidate)
                    reference_coverage["added_names"].append(str(candidate["name"]))
                reference_coverage["missing_after"] = [
                    ref.name for ref in missing_references(question, objects_data)
                ]
                timings["reference_repair_seconds"] = self._time_since(started)

        depth_matrix = None
        focal_length_px = None
        if self.use_depth:
            started = time.perf_counter()
            depth_matrix, focal_length_px = self.depth.estimate_depth(image)
            timings["depth_seconds"] = self._time_since(started)

        started = time.perf_counter()
        scene_graph = []
        for obj in objects_data:
            item: Dict[str, Any] = {
                "name": obj.get("name", "Unknown"),
                "point_2d": obj["point_2d"],
                "reason": obj.get("reason", ""),
            }
            if depth_matrix is not None:
                item["depth_meters"] = self.depth.sample_depth(depth_matrix, obj["point_2d"])
                if self.use_backprojection:
                    item["global_3d_position"] = self.depth.get_3d_coordinates(
                        depth_matrix, obj["point_2d"], focal_length_px
                    )

            if extraction_route == "line3_bbox":
                item["bbox_2d"] = obj.get("bbox_2d")
                if (
                    self.use_backprojection
                    and depth_matrix is not None
                    and item.get("bbox_2d")
                ):
                    dimensions = self.depth.get_3d_bbox_dimensions(
                        depth_matrix,
                        item["bbox_2d"],
                        item["point_2d"],
                        focal_length_px,
                    )
                    if dimensions:
                        item.update(dimensions)
            elif extraction_route == "line2_orientation":
                item["anchor_parts"] = obj.get("anchor_parts", "")
                item["visible_profile"] = obj.get("visible_profile", "unknown")
                item["2d_pointing_direction"] = obj.get("2d_pointing_direction", "unknown")
            else:
                item["facing_direction"] = obj.get("facing_direction", "Unknown")
            scene_graph.append(item)
        timings["grounding_seconds"] = self._time_since(started)

        spatial_relations_text = ""
        if self.use_symbolic_relations:
            started = time.perf_counter()
            if route == "line2_orientation":
                spatial_relations_text = generate_spatial_relations(scene_graph, target_perspective)
            elif route == "line3_bbox":
                spatial_relations_text = generate_bbox_relations(scene_graph)
            timings["relations_seconds"] = self._time_since(started)

        reasoning_context = spatial_relations_text
        if knowledge_text:
            if reasoning_context:
                reasoning_context += "\n\n"
            reasoning_context += "--- EXTERNAL DOMAIN KNOWLEDGE ---\n" + knowledge_text

        started = time.perf_counter()
        reasoning_scene_graph = scene_graph if self.use_scene_graph_context else []
        reasoning_evidence = reasoning_context if self.use_scene_graph_context else ""
        response = self.perception.perform_final_reasoning(
            image,
            question,
            options_text,
            reasoning_scene_graph,
            reasoning_evidence,
            task_route=route,
        )
        timings["final_reasoning_seconds"] = self._time_since(started)
        timings["total_seconds"] = self._time_since(total_start)
        return {
            "routing": decision.to_dict(),
            **self._trace_fields(
                decision,
                perception_raw_response,
                scene_graph,
                spatial_relations_text,
                response,
                perception_diagnostics,
                reference_coverage,
            ),
            "extraction_route": extraction_route,
            "target_perspective": target_perspective,
            "objects": scene_graph,
            "spatial_relations_text": spatial_relations_text,
            "knowledge_text": knowledge_text,
            "raw_response": response,
            "timings": timings,
        }
