"use client";

import { useEffect, useRef, useState } from "react";
import Graph from "graphology";
import { SigmaContainer, useLoadGraph, useRegisterEvents, useSigma } from "@react-sigma/core";
import "@react-sigma/core/lib/react-sigma.min.css";
import forceAtlas2 from "graphology-layout-forceatlas2";
import type { GraphNode, GraphEdge } from "@/types/graph";

interface GraphViewProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick: (nodeId: string) => void;
  selectedNodeId: string | null;
}

function GraphLoader({ nodes, edges, onNodeClick, selectedNodeId }: GraphViewProps) {
  const loadGraph = useLoadGraph();
  const sigma = useSigma();
  const registerEvents = useRegisterEvents();

  useEffect(() => {
    const graph = new Graph();

    // Color palette for clusters
    const clusterColors: Record<string, string> = {};
    const colors = [
      "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
      "#ec4899", "#14b8a6", "#f97316", "#06b6d4", "#84cc16",
    ];
    let colorIndex = 0;

    // Add nodes
    nodes.forEach((node) => {
      let color = "#9ca3af"; // Gray for unclustered
      if (node.cluster) {
        if (!clusterColors[node.cluster]) {
          clusterColors[node.cluster] = colors[colorIndex % colors.length];
          colorIndex++;
        }
        color = clusterColors[node.cluster];
      }

      graph.addNode(node.id, {
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: 5,
        label: node.label,
        color: node.id === selectedNodeId ? "#fbbf24" : color,
      });
    });

    // Add edges
    edges.forEach((edge) => {
      try {
        if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
          graph.addEdge(edge.source, edge.target, {
            size: edge.weight * 2,
            color: edge.edge_type === "connection" ? "#3b82f6" : "#d1d5db",
          });
        }
      } catch (e) {
        // Edge already exists, skip
      }
    });

    // Apply force-directed layout
    const settings = forceAtlas2.inferSettings(graph);
    forceAtlas2.assign(graph, {
      iterations: 50,
      settings,
    });

    loadGraph(graph);

    // Register click events
    registerEvents({
      clickNode: (event) => onNodeClick(event.node),
    });
  }, [nodes, edges, loadGraph, registerEvents, onNodeClick, selectedNodeId]);

  return null;
}

export function GraphView({ nodes, edges, onNodeClick, selectedNodeId }: GraphViewProps) {
  return (
    <div className="w-full h-[600px] border border-border rounded-lg overflow-hidden">
      <SigmaContainer
        style={{ width: "100%", height: "100%" }}
        settings={{
          renderEdgeLabels: false,
          defaultNodeColor: "#9ca3af",
          defaultEdgeColor: "#d1d5db",
        }}
      >
        <GraphLoader
          nodes={nodes}
          edges={edges}
          onNodeClick={onNodeClick}
          selectedNodeId={selectedNodeId}
        />
      </SigmaContainer>
    </div>
  );
}
