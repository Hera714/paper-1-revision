from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


ROUTES = (
    "line0_pure_vlm",
    "line1_base",
    "line2_orientation",
    "line3_bbox",
)


@dataclass(frozen=True)
class RoutingDecision:
    route: str
    confidence: float
    reason: str
    source: str
    proposed_route: Optional[str] = None
    raw_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QuestionOnlyRouter:
    """Select a route from question text only, using the already-loaded VLM.

    No benchmark category, sub-category, answer option, image, or hand-written
    keyword override is used. Low-confidence decisions fall back to the basic
    route so the behavior is explicit and reproducible.
    """

    PROMPT = """You are the controller of a spatial-reasoning pipeline.
Do not answer the question. Select the one processing route whose evidence is
most useful for solving it.

Available routes are defined by their computational capability:

1. line0_pure_vlm
   Use direct visual-language reasoning when extra metric geometry is unlikely
   to help and the decision mainly depends on global visual semantics or
   ordinary physical/common-sense interpretation.

2. line1_base
   Use object anchor points plus monocular depth and camera-centered 3D
   coordinates when basic position, depth, distance, or scene layout is enough.
   Questions about image-plane left/right/above/below/top/bottom/corners belong
   here; those words do not by themselves imply 3D depth or orientation.

3. line2_orientation
   Use pose-aware extraction and symbolic geometric reasoning when the answer
   depends on object orientation, facing direction, reference-frame changes,
   articulated angles, relative directions, or orientation-sensitive geometry.

4. line3_bbox
   Use bounding boxes and metric extent reasoning when the answer depends on
   physical size, width/height, visual alignment, overlap, coverage, or fit.

Selection cautions:
- Choose line3_bbox only when box extent is genuinely needed, normally for a
  small set of distinct objects. Do not choose it merely because many repeated
  objects form a row or must be counted.
- Explicit height/extreme-point questions such as tallest, shortest, highest,
  or lowest do require line3_bbox, even when the question mentions a line.
- For counting or long repeated sequences, prefer line0_pure_vlm unless basic
  anchor/depth evidence is explicitly needed.
- A distance question naming a landmark or reference object needs that reference
  extracted; normally choose line1_base unless orientation or box extent is the
  deciding evidence.
- Choose line2_orientation only when facing, rotation, viewpoint, angle, or an
  object-centered reference frame changes the answer.
- Visible wind direction inferred from smoke, flags, fabric, or vegetation is a
  global visual-semantic cue; use line0_pure_vlm unless an object's own pose is
  explicitly the reference frame.
- A generic question asking how objects are positioned uses line1_base. Do not
  use line3_bbox unless it explicitly asks about size, extent, alignment,
  overlap, coverage, fit, tallest/highest, or shortest/lowest.

Judge only from the question text. Return one JSON object and no other text:
{"route":"one valid route", "confidence":0.0, "reason":"short reason"}
"""

    def __init__(self, text_generator: Any, confidence_threshold: float = 0.55):
        self.text_generator = text_generator
        self.confidence_threshold = float(confidence_threshold)

    @staticmethod
    def parse_response(raw_response: str) -> Dict[str, Any]:
        raw = (raw_response or "").strip()
        if "</think>" in raw:
            raw = raw.split("</think>")[-1].strip()
        match = re.search(r"\{.*?\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)
        try:
            parsed = json.loads(raw)
        except Exception:
            return {
                "route": "line1_base",
                "confidence": 0.0,
                "reason": "Controller output was not valid JSON.",
            }

        route = parsed.get("route", "line1_base")
        if route not in ROUTES:
            route = "line1_base"
        try:
            confidence = min(1.0, max(0.0, float(parsed.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0
        reason = parsed.get("reason", "")
        if not isinstance(reason, str):
            reason = ""
        return {"route": route, "confidence": confidence, "reason": reason}

    def predict(self, question: str) -> RoutingDecision:
        messages = [{"role": "user", "content": [{"type": "text", "text": self.PROMPT + "\nQuestion:\n" + question}]}]
        raw = self.text_generator(messages, max_tokens=160, enable_thinking=False)
        parsed = self.parse_response(raw)
        proposed = parsed["route"]
        route = proposed
        reason = parsed["reason"]
        if parsed["confidence"] < self.confidence_threshold:
            route = "line1_base"
            reason = f"Low-confidence fallback from {proposed}. {reason}".strip()
        return RoutingDecision(
            route=route,
            confidence=parsed["confidence"],
            reason=reason,
            source="question_only_vlm",
            proposed_route=proposed,
            raw_response=raw,
        )


class OracleMetadataRouter:
    """Original metadata route, retained only as an upper-bound experiment."""

    LINE0 = {
        "3D Geometry": {"Volume Comparison"},
        "Depth & Occlusion": {"Reflective Surfaces"},
        "Orientation": {"Cardinal Direction"},
        "Relative Positioning": {"Betweenness Relationships"},
        "Size & Scale": {"Scale Consistency"},
        "Spatial Navigation": {"Accessibility Constraints", "Pathway Existence"},
    }
    LINE2 = {
        "Orientation": {"Facing Direction", "Object Rotation", "Stacking Orientation", "Tool Handedness"},
        "3D Geometry": {"Spatial Containment", "Shape Projection", "Gravity Effects"},
        "Depth & Occlusion": {"Complete Occlusion Inference", "Layering Order", "Partial Occlusion"},
        "Relative Positioning": {"Corner/Angle Positioning", "Directional Relations", "Proximity Gradients"},
    }
    LINE3 = {
        "Relative Positioning": {"Alignment Patterns"},
        "Size & Scale": {"*"},
    }

    @staticmethod
    def _matches(mapping: Dict[str, set], category: str, sub_category: str) -> bool:
        allowed = mapping.get(category, set())
        return sub_category in allowed or "*" in allowed

    def predict(self, question: str, *, category: str, sub_category: str) -> RoutingDecision:
        del question
        if self._matches(self.LINE0, category, sub_category):
            route = "line0_pure_vlm"
        elif self._matches(self.LINE2, category, sub_category):
            route = "line2_orientation"
        elif self._matches(self.LINE3, category, sub_category):
            route = "line3_bbox"
        else:
            route = "line1_base"
        return RoutingDecision(route, 1.0, "Original metadata assignment.", "oracle_metadata", route)


class FixedRouter:
    def __init__(self, route: str = "line1_base"):
        if route not in ROUTES:
            raise ValueError(f"Unknown fixed route: {route}")
        self.route = route

    def predict(self, question: str) -> RoutingDecision:
        del question
        return RoutingDecision(self.route, 1.0, "Fixed-route control.", "fixed", self.route)
