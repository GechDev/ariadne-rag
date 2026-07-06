"""Knowledge graph extraction from document text.

The extractor identifies named entities and the relationships between them.
The default extractor is deterministic and rule based so the pipeline is
reproducible and testable; an LLM-backed extractor can be swapped in later
behind the same interface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CAPITALIZED = re.compile(r"\b([A-Z][a-zA-Z]{1,}(?:\s+[A-Z][a-zA-Z]{1,}){0,3})\b")
_VERBS = re.compile(
    r"\b(?:is|are|was|were|founded|created|developed|built|established|leads|"
    r"leaded|runs|operates|produces|uses|has|have|contains|includes|supports|"
    r"provides|connects|links|located|based|situated|partners|collaborates|"
    r"works|depends|relies|depends_on|connected_to|related_to)\b",
    re.IGNORECASE,
)
_ARTICLES = {"the", "a", "an"}

# Words that appear in natural-language queries but are not entities.
_QUERY_STOPWORDS = {
    "what",
    "when",
    "where",
    "which",
    "who",
    "how",
    "tell",
    "about",
    "and",
    "for",
    "with",
    "from",
    "can",
    "you",
    "please",
    "me",
    "describe",
    "explain",
    "summarize",
    "summarise",
    "list",
    "give",
    "show",
    "find",
}


@dataclass(slots=True)
class ExtractedEntity:
    """A named entity with the chunk it was seen in."""

    name: str
    entity_type: str
    chunk_id: str


@dataclass(slots=True)
class ExtractedRelationship:
    """A relationship between two entities."""

    source: str
    target: str
    relationship: str
    chunk_id: str


class KnowledgeGraphExtractor:
    """Extract entities and relationships from chunked text."""

    def extract_entities(self, text: str, chunk_id: str) -> list[ExtractedEntity]:
        """Return capitalized noun phrases treated as entities."""
        seen: dict[str, ExtractedEntity] = {}
        for match in _CAPITALIZED.finditer(text):
            name = match.group(1).strip()
            if not self._is_meaningful_entity(name):
                continue
            entity_type = self._classify(name)
            key = name.lower()
            if key not in seen:
                seen[key] = ExtractedEntity(name=name, entity_type=entity_type, chunk_id=chunk_id)
        return list(seen.values())

    def extract_relationships(
        self, text: str, chunk_id: str
    ) -> list[ExtractedRelationship]:
        """Return verb-mediated relationships between co-occurring entities."""
        entities = self.extract_entities(text, chunk_id)
        names = [entity.name for entity in entities]
        if len(names) < 2:
            return []

        relationships: list[ExtractedRelationship] = []
        for sentence in re.split(r"[.!?]\s+", text):
            found = [name for name in names if name in sentence]
            if len(found) < 2:
                continue
            verb_match = _VERBS.search(sentence)
            relation = verb_match.group(0).lower() if verb_match else "associated_with"
            relationship = relation.replace(" ", "_")
            for source in found:
                for target in found:
                    if source == target:
                        continue
                    if not self._is_ordered(source, target, sentence, verb_match):
                        continue
                    relationships.append(
                        ExtractedRelationship(
                            source=source,
                            target=target,
                            relationship=relationship,
                            chunk_id=chunk_id,
                        )
                    )
        return relationships

    def _is_ordered(
        self, source: str, target: str, sentence: str, verb_match: re.Match | None
    ) -> bool:
        if verb_match is None:
            return sentence.find(source) < sentence.find(target)
        verb_index = verb_match.start()
        source_index = sentence.find(source)
        target_index = sentence.find(target)
        if source_index < target_index:
            return source_index < verb_index < target_index or target_index > source_index
        return target_index < verb_index < source_index

    @staticmethod
    def _is_meaningful_entity(name: str) -> bool:
        words = name.split()
        if any(word.lower() in _ARTICLES for word in words):
            return False
        return len(name) >= 2

    @staticmethod
    def _classify(name: str) -> str:
        lowered = name.lower()
        if any(kw in lowered for kw in ("university", "college", "school", "institute")):
            return "organization"
        if any(kw in lowered for kw in ("inc", "llc", "corp", "company", "ltd")):
            return "organization"
        if any(
            kw in lowered for kw in ("ml", "ai", "system", "engine", "platform", "model", "data")
        ):
            return "technology"
        return "concept"
