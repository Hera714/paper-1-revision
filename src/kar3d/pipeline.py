from __future__ import annotations

import time
from typing import Any, Dict, Optional

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
                "target_perspective": "camera",
                "objects": [],
                "spatial_relations_text": "",
                "knowledge_text": knowledge_text,
                "raw_response": response,
                "timings": timings,
            }

        extraction_route = route if self.use_fine_grained_features else "line1_base"
        started = time.perf_counter()
        target_perspective, objects_data = self.perception.extract_objects_3d(
            image,
            question,
            options_text,
            task_route=extraction_route,
        )
        timings["perception_seconds"] = self._time_since(started)

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
            "extraction_route": extraction_route,
            "target_perspective": target_perspective,
            "objects": scene_graph,
            "spatial_relations_text": spatial_relations_text,
            "knowledge_text": knowledge_text,
            "raw_response": response,
            "timings": timings,
        }
