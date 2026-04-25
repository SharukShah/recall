"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { WeakAreasResponse } from "@/types/analytics";

interface WeakAreasListProps {
  data: WeakAreasResponse;
}

export function WeakAreasList({ data }: WeakAreasListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Topics Needing Review</CardTitle>
        <p className="text-sm text-muted-foreground">
          Topics with lowest retention rates in the last 30 days
        </p>
      </CardHeader>
      <CardContent>
        {data.weak_areas.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No weak areas yet. Keep learning!
          </p>
        ) : (
          <div className="space-y-4">
            {data.weak_areas.map((area, index) => (
              <div key={index} className="space-y-2">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium line-clamp-2">{area.topic}</p>
                    <p className="text-xs text-muted-foreground">
                      {area.total_reviews} reviews • Avg: {area.avg_rating.toFixed(1)}/4 •{" "}
                      {area.lapsed_count} lapses
                    </p>
                  </div>
                  <div className="text-sm font-semibold text-red-600 ml-2">
                    {(area.retention_rate * 100).toFixed(0)}%
                  </div>
                </div>
                <Progress value={area.retention_rate * 100} className="h-2" />
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
