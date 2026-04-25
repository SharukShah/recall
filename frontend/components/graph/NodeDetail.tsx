"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { SkeletonCard } from "@/components/shared/SkeletonCard";
import { X, Calendar, FileText, Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { NodeDetailResponse } from "@/types/graph";

interface NodeDetailProps {
  nodeId: string | null;
  onClose: () => void;
}

const FSRS_STATE_LABELS: Record<number, { label: string; color: string }> = {
  0: { label: "New", color: "bg-blue-500" },
  1: { label: "Learning", color: "bg-yellow-500" },
  2: { label: "Review", color: "bg-green-500" },
  3: { label: "Relearning", color: "bg-red-500" },
};

export function NodeDetail({ nodeId, onClose }: NodeDetailProps) {
  const [detail, setDetail] = useState<NodeDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!nodeId) {
      setDetail(null);
      return;
    }

    const fetchDetail = async () => {
      setLoading(true);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${apiUrl}/api/knowledge/graph/node/${nodeId}`);
        if (!response.ok) throw new Error("Failed to fetch node detail");
        const data = await response.json();
        setDetail(data);
      } catch (error) {
        console.error("Error fetching node detail:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [nodeId]);

  if (!nodeId) return null;

  return (
    <Card className="absolute top-4 right-4 w-96 max-h-[80vh] overflow-y-auto shadow-lg z-10">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <CardTitle className="text-base">Node Details</CardTitle>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <SkeletonCard lines={5} />
        ) : detail ? (
          <div className="space-y-4">
            <div>
              <Badge variant="outline" className="mb-2">
                {detail.content_type}
              </Badge>
              <p className="text-sm">{detail.content}</p>
            </div>

            {detail.mnemonic_hint && (
              <div className="p-3 bg-muted rounded-lg">
                <p className="text-xs font-semibold text-muted-foreground mb-1">
                  Mnemonic Hint
                </p>
                <p className="text-sm italic">{detail.mnemonic_hint}</p>
              </div>
            )}

            <Separator />

            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <FileText className="h-3 w-3" />
                <span>From {detail.capture_source_type}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Calendar className="h-3 w-3" />
                <span>{new Date(detail.capture_created_at).toLocaleDateString()}</span>
              </div>
            </div>

            {detail.questions.length > 0 && (
              <>
                <Separator />
                <div className="space-y-2">
                  <p className="text-sm font-semibold flex items-center gap-2">
                    <Brain className="h-4 w-4" />
                    Review Questions ({detail.questions.length})
                  </p>
                  {detail.questions.slice(0, 3).map((q, i) => {
                    const stateInfo = FSRS_STATE_LABELS[q.state];
                    return (
                      <div
                        key={i}
                        className="p-2 bg-muted rounded text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <Badge className={stateInfo.color + " text-white"} variant="secondary">
                            {stateInfo.label}
                          </Badge>
                          <span className="text-muted-foreground">
                            {new Date(q.due).toLocaleDateString()}
                          </span>
                        </div>
                        <p>{q.question_text}</p>
                      </div>
                    );
                  })}
                </div>
              </>
            )}

            {detail.connected_nodes.length > 0 && (
              <>
                <Separator />
                <div className="space-y-2">
                  <p className="text-sm font-semibold">
                    Connected Concepts ({detail.connected_nodes.length})
                  </p>
                  {detail.connected_nodes.map((node, i) => (
                    <div key={i} className="p-2 bg-muted rounded text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">
                          {(node.similarity * 100).toFixed(0)}% similar
                        </span>
                      </div>
                      <p className="text-muted-foreground">{node.content}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Failed to load details</p>
        )}
      </CardContent>
    </Card>
  );
}
