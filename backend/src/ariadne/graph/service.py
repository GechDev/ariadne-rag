"""Knowledge graph extraction service.

Runs the entity/relationship extractor over document chunks and persists the
result into the graph store so retrieval can traverse it.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ariadne.graph.extraction import KnowledgeGraphExtractor
from ariadne.graph.store import GraphStore
from ariadne.logging import get_logger
from ariadne.models import Chunk

logger = get_logger("graph.service")


class GraphExtractionService:
    """Build the document knowledge graph from its chunks."""

    def __init__(
        self,
        extractor: KnowledgeGraphExtractor | None = None,
        store: GraphStore | None = None,
    ) -> None:
        self.extractor = extractor or KnowledgeGraphExtractor()
        self.store = store or GraphStore()

    def build_document_graph(self, session: Session, document_id: str, chunks: list[Chunk]) -> dict:
        """Extract and persist entities and relationships for a document."""
        entity_data: dict[str, dict] = {}
        relationship_data: dict[tuple[str, str, str], dict] = {}
        relationship_keys: set[tuple[str, str, str]] = set()

        for chunk in chunks:
            for entity in self.extractor.extract_entities(chunk.text, chunk.id):
                entity_key = entity.name.lower()
                entry = entity_data.setdefault(
                    entity_key,
                    {
                        "name": entity.name,
                        "entity_type": entity.entity_type,
                        "chunk_ids": set(),
                    },
                )
                entry["chunk_ids"].add(chunk.id)

            for relationship in self.extractor.extract_relationships(chunk.text, chunk.id):
                relationship_key = (
                    relationship.source.lower(),
                    relationship.target.lower(),
                    relationship.relationship,
                )
                if relationship_key in relationship_keys:
                    continue
                relationship_keys.add(relationship_key)
                entry = relationship_data.setdefault(
                    relationship_key,
                    {
                        "source": relationship.source,
                        "target": relationship.target,
                        "relationship": relationship.relationship,
                        "chunk_ids": set(),
                    },
                )
                entry["chunk_ids"].add(chunk.id)

        entities = [
            {
                "name": entry["name"],
                "entity_type": entry["entity_type"],
                "chunk_ids": sorted(entry["chunk_ids"]),
            }
            for entry in entity_data.values()
        ]
        relationships = [
            {
                "source": entry["source"],
                "target": entry["target"],
                "relationship": entry["relationship"],
                "chunk_ids": sorted(entry["chunk_ids"]),
            }
            for entry in relationship_data.values()
        ]

        self.store.save_document_graph(session, document_id, entities, relationships)
        logger.info(
            "knowledge graph built",
            extra={
                "document_id": document_id,
                "entities": len(entities),
                "relationships": len(relationships),
            },
        )
        return {"entities": len(entities), "relationships": len(relationships)}

    def query_entities_from_text(self, text: str) -> list[str]:
        """Extract entity names from a natural-language query."""
        from ariadne.graph.extraction import _QUERY_STOPWORDS

        entities = self.extractor.extract_entities(text, chunk_id="query")
        return [entity.name for entity in entities if entity.name.lower() not in _QUERY_STOPWORDS]
