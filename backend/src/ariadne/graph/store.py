"""Knowledge graph persistence and traversal.

The graph store persists entities and relationships per document and offers
traversal queries used by graph-based retrieval: finding entities related to
a set of seed concepts and the chunks that mention them.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import networkx as nx  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from ariadne.logging import get_logger
from ariadne.models import GraphEntity, GraphRelationship

logger = get_logger("graph.store")


@dataclass(slots=True)
class GraphNode:
    """An entity with the chunks that mention it."""

    entity_id: str
    name: str
    entity_type: str
    chunk_ids: list[str]


@dataclass(slots=True)
class GraphMatch:
    """A chunk surfaced by graph traversal, with an aggregate score."""

    chunk_id: str
    document_id: str
    entities: list[str]
    score: float


class GraphStore:
    """Persist and query the document knowledge graph."""

    def save_document_graph(
        self,
        session: Session,
        document_id: str,
        entities: list[dict],
        relationships: list[dict],
    ) -> None:
        """Replace the graph for a document with fresh extractions."""
        session.query(GraphEntity).filter(GraphEntity.document_id == document_id).delete(
            synchronize_session=False
        )
        session.query(GraphRelationship).filter(
            GraphRelationship.document_id == document_id
        ).delete(synchronize_session=False)
        session.flush()

        entity_map: dict[str, GraphEntity] = {}
        for item in entities:
            entity = session.scalar(
                select(GraphEntity).where(
                    GraphEntity.document_id == document_id,
                    GraphEntity.name == item["name"],
                )
            )
            if entity is None:
                entity = GraphEntity(
                    document_id=document_id,
                    name=item["name"],
                    entity_type=item.get("entity_type", "concept"),
                    chunk_ids=item.get("chunk_ids", []),
                )
                session.add(entity)
            else:
                entity.chunk_ids = list(set(entity.chunk_ids) | set(item.get("chunk_ids", [])))
                entity.frequency += 1
            session.flush()
            entity_map[item["name"].lower()] = entity

        for item in relationships:
            source = entity_map.get(item["source"].lower())
            target = entity_map.get(item["target"].lower())
            if source is None or target is None or source.id == target.id:
                continue
            existing = session.scalar(
                select(GraphRelationship).where(
                    GraphRelationship.document_id == document_id,
                    GraphRelationship.source_id == source.id,
                    GraphRelationship.target_id == target.id,
                    GraphRelationship.relationship == item["relationship"],
                )
            )
            if existing is None:
                session.add(
                    GraphRelationship(
                        document_id=document_id,
                        source_id=source.id,
                        target_id=target.id,
                        relationship=item["relationship"],
                        weight=1.0,
                        chunk_ids=item.get("chunk_ids", []),
                    )
                )
            else:
                existing.weight += 1.0
                existing.chunk_ids = list(
                    set(existing.chunk_ids) | set(item.get("chunk_ids", []))
                )
        session.flush()

    def get_document_graph(self, session: Session, document_id: str) -> nx.DiGraph:
        """Load the document graph as a networkx DiGraph."""
        graph = nx.DiGraph()
        entities = session.scalars(
            select(GraphEntity).where(GraphEntity.document_id == document_id)
        )
        for entity in entities:
            graph.add_node(
                entity.id,
                name=entity.name,
                entity_type=entity.entity_type,
                chunk_ids=list(entity.chunk_ids),
                document_id=document_id,
            )
        relationships = session.scalars(
            select(GraphRelationship).where(GraphRelationship.document_id == document_id)
        )
        for relationship in relationships:
            graph.add_edge(
                relationship.source_id,
                relationship.target_id,
                relationship=relationship.relationship,
                weight=relationship.weight,
                chunk_ids=list(relationship.chunk_ids),
            )
        return graph

    def get_document_nodes(self, session: Session, document_id: str) -> list[GraphNode]:
        """Return the entities of a document as lightweight nodes."""
        entities = session.scalars(
            select(GraphEntity).where(GraphEntity.document_id == document_id)
        )
        return [
            GraphNode(
                entity_id=entity.id,
                name=entity.name,
                entity_type=entity.entity_type,
                chunk_ids=list(entity.chunk_ids),
            )
            for entity in entities
        ]

    def search(
        self,
        session: Session,
        query_entities: list[str],
        *,
        document_ids: list[str] | None = None,
        depth: int = 1,
        top_k: int = 10,
    ) -> list[GraphMatch]:
        """Find chunks near the query entities, aggregating by proximity."""
        query_entity_names = {name.lower() for name in query_entities}
        if not query_entity_names:
            return []

        stmt = select(GraphEntity)
        if document_ids:
            stmt = stmt.where(GraphEntity.document_id.in_(document_ids))
        entities = list(session.scalars(stmt))

        if not entities:
            return []

        by_name: dict[str, list[GraphEntity]] = defaultdict(list)
        for entity in entities:
            by_name[entity.name.lower()].append(entity)

        matched: set[str] = set()
        for name in query_entity_names:
            matched.update(entity.id for entity in by_name.get(name, []))

        if not matched:
            return []

        by_id = {entity.id: entity for entity in entities}
        relationships = session.scalars(select(GraphRelationship)).all()
        # entity_id -> [(target_id, rel)]
        adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for relationship in relationships:
            adjacency[relationship.source_id].append(
                (relationship.target_id, relationship.relationship)
            )
            adjacency[relationship.target_id].append(
                (relationship.source_id, relationship.relationship)
            )

        scores: dict[str, float] = defaultdict(float)
        for entity_id in matched:
            scores[entity_id] += 1.0
            frontier = [entity_id]
            for hop in range(depth):
                next_frontier: list[str] = []
                for node in frontier:
                    for neighbor, _relationship in adjacency.get(node, []):
                        if neighbor not in scores:
                            scores[neighbor] += 0.5 ** (hop + 1)
                            next_frontier.append(neighbor)
                frontier = next_frontier

        chunk_scores: dict[str, dict] = defaultdict(
            lambda: {"score": 0.0, "entities": set(), "document_id": None}
        )
        for entity_id, score in scores.items():
            graph_entity = by_id.get(entity_id)
            if graph_entity is None:
                continue
            for chunk_id in graph_entity.chunk_ids:
                chunk_scores[chunk_id]["score"] += score
                chunk_scores[chunk_id]["entities"].add(graph_entity.name)
                chunk_scores[chunk_id]["document_id"] = graph_entity.document_id

        ranked = sorted(
            chunk_scores.items(),
            key=lambda item: (item[1]["score"], len(item[1]["entities"])),
            reverse=True,
        )[:top_k]

        return [
            GraphMatch(
                chunk_id=chunk_id,
                document_id=info["document_id"],
                entities=sorted(info["entities"]),
                score=info["score"],
            )
            for chunk_id, info in ranked
        ]

    def delete_document(self, session: Session, document_id: str) -> int:
        """Remove the document graph. Returns total rows removed."""
        entities = session.query(GraphEntity).filter(
            GraphEntity.document_id == document_id
        ).delete(synchronize_session=False)
        relationships = session.query(GraphRelationship).filter(
            GraphRelationship.document_id == document_id
        ).delete(synchronize_session=False)
        session.flush()
        return entities + relationships
