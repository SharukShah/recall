export interface GraphNode {
  id: string;
  label: string;
  content: string;
  content_type: string;
  capture_id: string;
  created_at: string;
  cluster: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  edge_type: "similarity" | "connection";
}

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  total_clusters: number;
}

export interface GraphDataResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: GraphStats;
}

export interface NodeQuestion {
  question_text: string;
  question_type: string;
  state: number;
  due: string;
}

export interface ConnectedNode {
  id: string;
  content: string;
  similarity: number;
}

export interface NodeDetailResponse {
  id: string;
  content: string;
  content_type: string;
  mnemonic_hint: string | null;
  capture_raw_text: string;
  capture_source_type: string;
  capture_created_at: string;
  questions: NodeQuestion[];
  connected_nodes: ConnectedNode[];
}
