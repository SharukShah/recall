"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Lightbulb } from "lucide-react";

interface ChunkCardProps {
  title: string;
  content: string;
  analogy: string | null;
  chunkIndex: number;
  totalChunks: number;
}

export function ChunkCard({ title, content, analogy, chunkIndex, totalChunks }: ChunkCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{title}</CardTitle>
          <Badge variant="secondary">
            {chunkIndex + 1} / {totalChunks}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="text-sm leading-relaxed whitespace-pre-wrap">
          {content}
        </div>
        {analogy && (
          <div className="flex items-start gap-2 p-3 bg-primary/5 rounded-md border border-primary/10">
            <Lightbulb className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <p className="text-sm text-muted-foreground italic">{analogy}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
