"use client";

import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SearchSource } from "@/types/api";

interface SourceCardProps {
  source: SearchSource;
}

export function SourceCard({ source }: SourceCardProps) {
  const date = new Date(source.captured_at).toLocaleDateString();
  const similarityPct = Math.round(source.similarity * 100);

  return (
    <Card className="transition-colors hover:bg-muted/50">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-sm font-medium text-muted-foreground">
                [{source.index}]
              </span>
              <Badge variant="secondary" className="text-xs">
                {source.content_type}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {similarityPct}% match
              </span>
            </div>
            <p className="text-sm leading-relaxed">{source.content}</p>
            <div className="flex items-center gap-3 mt-2">
              <span className="text-xs text-muted-foreground">
                Captured {date}
              </span>
              <Link
                href={`/history/${source.capture_id}`}
                className="text-xs text-primary hover:underline"
              >
                View capture
              </Link>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
