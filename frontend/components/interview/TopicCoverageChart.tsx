"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { TopicCoverageResponse } from "@/types/api";
import { BarChart3 } from "lucide-react";

interface TopicCoverageChartProps {
  data: TopicCoverageResponse;
}

export function TopicCoverageChart({ data }: TopicCoverageChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          Topic Coverage
        </CardTitle>
        {data.uncategorized_count > 0 && (
          <p className="text-xs text-muted-foreground">
            {data.uncategorized_count} uncategorized questions
          </p>
        )}
      </CardHeader>
      <CardContent>
        {data.categories.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No topic data yet. Start capturing and reviewing!
          </p>
        ) : (
          <div className="space-y-4">
            {data.categories.map((cat) => {
              const masteredPct = cat.total_questions > 0
                ? Math.round((cat.mastered_count / cat.total_questions) * 100)
                : 0;
              const reviewedPct = cat.total_questions > 0
                ? Math.round((cat.reviewed_count / cat.total_questions) * 100)
                : 0;

              const barColor =
                masteredPct > 80
                  ? "bg-green-500"
                  : masteredPct >= 50
                    ? "bg-yellow-500"
                    : "bg-red-500";

              return (
                <div key={cat.category} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium capitalize">
                      {cat.category.replace("_", " ")}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {cat.total_questions === 0 ? (
                        "No questions yet"
                      ) : (
                        `${cat.mastered_count}/${cat.total_questions} mastered`
                      )}
                    </span>
                  </div>
                  {cat.total_questions > 0 && (
                    <div className="relative h-2 w-full rounded-full bg-muted overflow-hidden">
                      {/* Reviewed (lighter) behind mastered (solid) */}
                      <div
                        className="absolute inset-y-0 left-0 rounded-full bg-muted-foreground/20"
                        style={{ width: `${reviewedPct}%` }}
                      />
                      <div
                        className={`absolute inset-y-0 left-0 rounded-full ${barColor}`}
                        style={{ width: `${masteredPct}%` }}
                      />
                    </div>
                  )}
                  {cat.total_questions > 0 && (
                    <div className="flex gap-3 text-[10px] text-muted-foreground">
                      <span>{reviewedPct}% reviewed</span>
                      <span>{masteredPct}% mastered</span>
                      {cat.weak_count > 0 && (
                        <span className="text-red-500">{cat.weak_count} weak</span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
