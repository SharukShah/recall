"""
Graph service — generate knowledge graph data from extracted points.
Includes 30-second caching to reduce DB load on O(n²) similarity queries.
"""
from asyncpg import Pool
from datetime import datetime, timedelta
from models.graph_models import (
    GraphDataResponse,
    GraphNode,
    GraphEdge,
    GraphStats,
    NodeDetailResponse,
    NodeQuestion,
    ConnectedNode,
)


# Simple in-memory cache with TTL
_graph_cache: dict[str, tuple[GraphDataResponse, datetime]] = {}
_cache_ttl = timedelta(seconds=30)


class GraphService:
    """Service for generating knowledge graph visualization data."""

    def __init__(self, db_pool: Pool):
        self.db_pool = db_pool

    async def get_graph_data(
        self, min_similarity: float = 0.7, limit: int = 200
    ) -> GraphDataResponse:
        """
        Get graph nodes and edges.
        
        Nodes = extracted_points with embeddings
        Edges = pgvector similarity (>= min_similarity) + connection_questions
        
        Results are cached for 30 seconds to reduce load on expensive CROSS JOIN.
        """
        # Check cache
        cache_key = f"{min_similarity}:{limit}"
        if cache_key in _graph_cache:
            cached_data, cached_time = _graph_cache[cache_key]
            if datetime.now() - cached_time < _cache_ttl:
                return cached_data
        
        # Fetch fresh data
        async with self.db_pool.acquire() as conn:
            # Fetch nodes (extracted points with embeddings)
            nodes_query = """
                SELECT 
                    ep.id,
                    ep.content,
                    ep.content_type,
                    ep.capture_id,
                    ep.created_at
                FROM extracted_points ep
                WHERE ep.embedding IS NOT NULL
                ORDER BY ep.created_at DESC
                LIMIT $1
            """
            rows = await conn.fetch(nodes_query, limit)
            
            nodes = [
                GraphNode(
                    id=str(row["id"]),
                    label=row["content"][:60] + ("..." if len(row["content"]) > 60 else ""),
                    content=row["content"],
                    content_type=row["content_type"] or "fact",
                    capture_id=str(row["capture_id"]),
                    created_at=row["created_at"].isoformat(),
                    cluster=row["content_type"],  # Use content_type as cluster
                )
                for row in rows
            ]

            if not nodes:
                return GraphDataResponse(
                    nodes=[],
                    edges=[],
                    stats=GraphStats(total_nodes=0, total_edges=0, total_clusters=0),
                )

            node_ids = [node.id for node in nodes]

            # Compute similarity edges using pgvector
            similarity_query = """
                SELECT 
                    a.id::text as source,
                    b.id::text as target,
                    1 - (a.embedding <=> b.embedding) as similarity
                FROM extracted_points a
                CROSS JOIN extracted_points b
                WHERE a.id = ANY($1::uuid[])
                  AND b.id = ANY($1::uuid[])
                  AND a.id < b.id
                  AND a.embedding IS NOT NULL
                  AND b.embedding IS NOT NULL
                  AND 1 - (a.embedding <=> b.embedding) >= $2
                ORDER BY similarity DESC
                LIMIT 500
            """
            similarity_rows = await conn.fetch(
                similarity_query, node_ids, min_similarity
            )

            edges = [
                GraphEdge(
                    source=row["source"],
                    target=row["target"],
                    weight=float(row["similarity"]),
                    edge_type="similarity",
                )
                for row in similarity_rows
            ]

            # Add explicit connection edges from connection_questions
            connection_query = """
                SELECT DISTINCT
                    point_a_id::text as source,
                    point_b_id::text as target
                FROM connection_questions
                WHERE point_a_id = ANY($1::uuid[])
                  AND point_b_id = ANY($1::uuid[])
            """
            connection_rows = await conn.fetch(connection_query, node_ids)

            for row in connection_rows:
                # Avoid duplicates
                source, target = row["source"], row["target"]
                if source > target:
                    source, target = target, source
                if not any(
                    e.source == source and e.target == target for e in edges
                ):
                    edges.append(
                        GraphEdge(
                            source=source,
                            target=target,
                            weight=1.0,
                            edge_type="connection",
                        )
                    )

            # Count clusters
            clusters = set(node.cluster for node in nodes if node.cluster)

            stats = GraphStats(
                total_nodes=len(nodes),
                total_edges=len(edges),
                total_clusters=len(clusters),
            )

            result = GraphDataResponse(nodes=nodes, edges=edges, stats=stats)
            
            # Cache result
            _graph_cache[cache_key] = (result, datetime.now())
            
            return result

    async def get_node_detail(self, point_id: str) -> NodeDetailResponse | None:
        """Get detailed info for a specific node."""
        async with self.db_pool.acquire() as conn:
            # Fetch point and capture info
            point_query = """
                SELECT 
                    ep.id,
                    ep.content,
                    ep.content_type,
                    ep.mnemonic_hint,
                    ep.created_at,
                    c.raw_text,
                    c.source_type,
                    c.created_at as capture_created_at
                FROM extracted_points ep
                JOIN captures c ON ep.capture_id = c.id
                WHERE ep.id = $1
            """
            point_row = await conn.fetchrow(point_query, point_id)
            if not point_row:
                return None

            # Fetch questions linked to this point
            questions_query = """
                SELECT 
                    question_text,
                    question_type,
                    state,
                    due
                FROM questions
                WHERE source_point_id = $1
                ORDER BY created_at
            """
            question_rows = await conn.fetch(questions_query, point_id)
            questions = [
                NodeQuestion(
                    question_text=row["question_text"],
                    question_type=row["question_type"],
                    state=row["state"],
                    due=row["due"].isoformat(),
                )
                for row in question_rows
            ]

            # Fetch connected nodes (top 5 by similarity)
            connected_query = """
                SELECT 
                    b.id::text,
                    b.content,
                    1 - (a.embedding <=> b.embedding) as similarity
                FROM extracted_points a
                CROSS JOIN extracted_points b
                WHERE a.id = $1
                  AND b.id != $1
                  AND a.embedding IS NOT NULL
                  AND b.embedding IS NOT NULL
                ORDER BY similarity DESC
                LIMIT 5
            """
            connected_rows = await conn.fetch(connected_query, point_id)
            connected_nodes = [
                ConnectedNode(
                    id=row["id"],
                    content=row["content"],
                    similarity=float(row["similarity"]),
                )
                for row in connected_rows
            ]

            return NodeDetailResponse(
                id=str(point_row["id"]),
                content=point_row["content"],
                content_type=point_row["content_type"] or "fact",
                mnemonic_hint=point_row["mnemonic_hint"],
                capture_raw_text=point_row["raw_text"],
                capture_source_type=point_row["source_type"],
                capture_created_at=point_row["capture_created_at"].isoformat(),
                questions=questions,
                connected_nodes=connected_nodes,
            )
