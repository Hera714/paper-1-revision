"""Conservative question-reference checks using inference-time text only.

This module intentionally does not infer new objects from answer choices. It only
identifies explicit spatial reference phrases in the question, so a missing match
can trigger review without treating options such as ``Nothing`` as scene objects.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


_TRIGGERS = (
    ("between", re.compile(r"\bbetween\s+", re.I), 2),
    ("closest_to", re.compile(r"\bclosest\s+to\s+", re.I), 1),
    ("away_from", re.compile(r"\b(?:further|farther)\s+away\s+from\s+", re.I), 1),
    ("aligned_with", re.compile(r"\baligned\s+with\s+", re.I), 2),
    ("inside", re.compile(r"\binside\s+", re.I), 1),
    ("near", re.compile(r"\bnear\s+", re.I), 1),
    ("deeper_than", re.compile(r"\bdeeper\s+than\s+", re.I), 1),
    ("shallower_than", re.compile(r"\bshallower\s+than\s+", re.I), 1),
)
_BOUNDARY = re.compile(
    r"\s*(?:[,?.;:]|\b(?:and|but|than|near|with|from|for|on|in|at|to|"
    r"which|who|when|where|that|while|because|if|is|are|was|were|"
    r"would|could|can|aligned|filled|wearing|placed)\b)",
    re.I,
)
_ARTICLES = {"the", "a", "an"}
_NON_ENTITY = {
    "nothing", "none", "not given", "can't answer", "cannot answer", "unknown",
    "no object", "no objects", "all of the above", "yes", "no", "true", "false",
}
_GENERIC_HEADS = {
    "viewer", "camera", "image", "photo", "photograph", "scene", "picture",
    "other", "another", "one", "ones", "it", "them", "each", "all", "way",
    "object", "item", "thing", "aligned",
    "center", "corner", "edge", "top", "bottom", "space", "length",
    "direction", "side", "point", "viewpoint", "frame", "background",
    "area", "spacing", "gap",
}
_HEAD_ALIASES = {
    "doorway": {"door"}, "door": {"doorway"},
    "sitter": {"person", "people", "seated"},
}


@dataclass(frozen=True)
class Reference:
    name: str
    relation: str


def _normalize_words(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.casefold().replace("'s", ""))
    return [word for word in words if word not in _ARTICLES]


def _head(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def _phrase(text: str) -> str:
    text = _BOUNDARY.split(text, maxsplit=1)[0].strip(" -'\"()")
    words = _normalize_words(text)
    if not words or len(words) > 5:
        return ""
    if words[0] in {"edge", "center", "corner", "top", "bottom", "space"}:
        return ""
    head = _head(words[-1])
    if head in _GENERIC_HEADS or " ".join(words) in _NON_ENTITY:
        return ""
    return " ".join(words)


def question_references(question: str) -> list[Reference]:
    """Return only high-confidence *explicit* references, never option-derived names."""
    references: list[Reference] = []
    seen: set[str] = set()
    for relation, pattern, arity in _TRIGGERS:
        for match in pattern.finditer(question):
            tail = question[match.end():]
            first = _phrase(tail)
            phrases = [first]
            if arity == 2 and first:
                conjunction = re.search(r"\band\b", tail[:100], re.I)
                if conjunction:
                    phrases.append(_phrase(tail[conjunction.end():]))
            for phrase in phrases:
                if phrase and phrase not in seen:
                    seen.add(phrase)
                    references.append(Reference(phrase, relation))
    return references


def reference_present(reference: Reference, objects: list[dict]) -> bool:
    """Match the noun head, allowing modifiers in the question or scene label."""
    words = _normalize_words(reference.name)
    if not words:
        return True
    head = _head(words[-1])
    alternatives = {head} | _HEAD_ALIASES.get(head, set())
    for obj in objects:
        name_words = {_head(word) for word in _normalize_words(str(obj.get("name", "")))}
        if alternatives & name_words:
            return True
    return False


def missing_references(question: str, objects: list[dict]) -> list[Reference]:
    return [ref for ref in question_references(question) if not reference_present(ref, objects)]


def non_entity_object_names(objects: list[dict]) -> list[str]:
    """Find clearly non-physical answer labels mistakenly emitted as objects."""
    return [str(obj.get("name", "")) for obj in objects
            if is_non_entity_name(str(obj.get("name", "")))]


def is_non_entity_name(name: str) -> bool:
    return name.strip().casefold() in _NON_ENTITY
