"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ZoomIn, ZoomOut, Maximize } from "lucide-react";
import { Slider } from "@/components/ui/slider";

interface GraphControlsProps {
  minSimilarity: number;
  onMinSimilarityChange: (value: number) => void;
  onRefresh: () => void;
  nodeCount: number;
  edgeCount: number;
}

export function GraphControls({
  minSimilarity,
  onMinSimilarityChange,
  onRefresh,
  nodeCount,
  edgeCount,
}: GraphControlsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Graph Controls</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Minimum Similarity: {minSimilarity.toFixed(2)}</Label>
          <Slider
            value={[minSimilarity]}
            onValueChange={(values) => onMinSimilarityChange(values[0])}
            min={0.5}
            max={0.95}
            step={0.05}
            className="w-full"
          />
        </div>

        <Button onClick={onRefresh} variant="outline" className="w-full">
          <Maximize className="h-4 w-4 mr-2" />
          Refresh Graph
        </Button>

        <div className="pt-4 border-t space-y-1 text-sm text-muted-foreground">
          <div className="flex justify-between">
            <span>Nodes:</span>
            <span className="font-semibold">{nodeCount}</span>
          </div>
          <div className="flex justify-between">
            <span>Edges:</span>
            <span className="font-semibold">{edgeCount}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
