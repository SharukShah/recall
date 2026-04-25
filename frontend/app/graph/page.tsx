"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { PageHeader } from "@/components/shared/PageHeader";
import { SkeletonCard } from "@/components/shared/SkeletonCard";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { getGraphData } from "@/lib/api";
import type { GraphDataResponse } from "@/types/graph";

// Dynamically import graph components to avoid SSR issues with WebGL
const GraphView = dynamic(() => import("@/components/graph/GraphView").then(m => ({ default: m.GraphView })), { ssr: false });
const GraphControls = dynamic(() => import("@/components/graph/GraphControls").then(m => ({ default: m.GraphControls })), { ssr: false });
const NodeDetail = dynamic(() => import("@/components/graph/NodeDetail").then(m => ({ default: m.NodeDetail })), { ssr: false });

export default function GraphPage() {
  const [graphData, setGraphData] = useState<GraphDataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [minSimilarity, setMinSimilarity] = useState(0.7);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  useEffect(() => {
    fetchGraphData();
  }, [minSimilarity]);

  const fetchGraphData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getGraphData(minSimilarity, 200);
      setGraphData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load graph");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Knowledge Graph" />
        <SkeletonCard lines={10} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Knowledge Graph" />
        <ErrorState message={error} onRetry={fetchGraphData} />
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader title="Knowledge Graph" />
        <EmptyState
          message="No knowledge graph yet"
          subMessage="Capture at least 5 items with extracted knowledge points to see connections."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 relative">
      <PageHeader title="Knowledge Graph" />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <GraphControls
            minSimilarity={minSimilarity}
            onMinSimilarityChange={setMinSimilarity}
            onRefresh={fetchGraphData}
            nodeCount={graphData.stats.total_nodes}
            edgeCount={graphData.stats.total_edges}
          />
        </div>

        <div className="lg:col-span-3 relative">
          <GraphView
            nodes={graphData.nodes}
            edges={graphData.edges}
            onNodeClick={setSelectedNodeId}
            selectedNodeId={selectedNodeId}
          />
          <NodeDetail nodeId={selectedNodeId} onClose={() => setSelectedNodeId(null)} />
        </div>
      </div>
    </div>
  );
}
