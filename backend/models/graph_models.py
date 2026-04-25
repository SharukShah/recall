"""Pydantic models for Knowledge Graph endpoints."""
from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    label: str  # First 60 chars of content
    content: str  # Full content
    content_type: str  # fact, concept, etc.
    capture_id: str
    created_at: str
    cluster: str | None  # Topic cluster label (from capture topic)


class GraphEdge(BaseModel):
    source: str  # point_id
    target: str  # point_id
    weight: float  # Similarity score or 1.0 for explicit connections
    edge_type: str  # "similarity" | "connection"


class GraphStats(BaseModel):
    total_nodes: int
    total_edges: int
    total_clusters: int


class GraphDataResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: GraphStats


class NodeQuestion(BaseModel):
    question_text: str
    question_type: str
    state: int
    due: str


class ConnectedNode(BaseModel):
    id: str
    content: str
    similarity: float


class NodeDetailResponse(BaseModel):
    id: str
    content: str
    content_type: str
    mnemonic_hint: str | None
    capture_raw_text: str
    capture_source_type: str
    capture_created_at: str
    questions: list[NodeQuestion]
    connected_nodes: list[ConnectedNode]
