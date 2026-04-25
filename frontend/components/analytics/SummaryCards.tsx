"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { AnalyticsSummary } from "@/types/analytics";

interface SummaryCardsProps {
  data: AnalyticsSummary;
}

export function SummaryCards({ data }: SummaryCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card>
        <CardContent className="pt-6">
          <div className="text-center">
            <p className="text-4xl font-bold text-primary">{data.total_reviews_all_time}</p>
            <p className="text-sm text-muted-foreground mt-1">Total Reviews</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <div className="text-center">
            <p className="text-4xl font-bold text-primary">
              {data.avg_score !== null ? data.avg_score.toFixed(2) : "—"}
            </p>
            <p className="text-sm text-muted-foreground mt-1">Average Score (1-4)</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <div className="text-center">
            <p className="text-4xl font-bold text-primary">
              {Math.floor(data.total_time_studying_estimate_minutes / 60)}h{" "}
              {data.total_time_studying_estimate_minutes % 60}m
            </p>
            <p className="text-sm text-muted-foreground mt-1">Study Time Estimate</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
