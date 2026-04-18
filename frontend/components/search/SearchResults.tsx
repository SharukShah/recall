"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SourceCard } from "./SourceCard";
import type { SearchResponse } from "@/types/api";

interface SearchResultsProps {
  data: SearchResponse;
}

export function SearchResults({ data }: SearchResultsProps) {
  return (
    <div className="space-y-6 animate-crossfade-in">
      {/* Answer */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            {data.has_answer ? "Answer" : "No results"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {data.answer}
          </p>
        </CardContent>
      </Card>

      {/* Sources */}
      {data.sources.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">
            Sources ({data.result_count})
          </h3>
          {data.sources.map((source) => (
            <SourceCard key={source.index} source={source} />
          ))}
        </div>
      )}
    </div>
  );
}
