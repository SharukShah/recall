"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Flame, Calendar, TrendingUp } from "lucide-react";
import type { ReviewConsistency } from "@/types/analytics";

interface ConsistencyStatsProps {
  data: ReviewConsistency;
}

export function ConsistencyStats({ data }: ConsistencyStatsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Review Consistency</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-orange-100 dark:bg-orange-950">
              <Flame className="h-5 w-5 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{data.current_streak}</p>
              <p className="text-xs text-muted-foreground">Day Streak</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-950">
              <TrendingUp className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{data.longest_streak}</p>
              <p className="text-xs text-muted-foreground">Longest Streak</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-100 dark:bg-green-950">
              <Calendar className="h-5 w-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{data.review_days_last_30}</p>
              <p className="text-xs text-muted-foreground">Active Days (30d)</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-950">
              <Calendar className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{data.avg_reviews_per_day.toFixed(1)}</p>
              <p className="text-xs text-muted-foreground">Reviews/Day (30d)</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
