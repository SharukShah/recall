"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ActivityResponse, ActivityDay } from "@/types/analytics";

interface ActivityHeatmapProps {
  data: ActivityResponse;
}

export function ActivityHeatmap({ data }: ActivityHeatmapProps) {
  const getColor = (captures: number, reviews: number) => {
    const total = captures + reviews;
    if (total === 0) return "bg-muted";
    if (total <= 3) return "bg-green-200 dark:bg-green-900";
    if (total <= 7) return "bg-green-400 dark:bg-green-700";
    if (total <= 12) return "bg-green-600 dark:bg-green-500";
    return "bg-green-800 dark:bg-green-300";
  };

  // Group days into weeks
  const weeks: ActivityDay[][] = [];
  for (let i = 0; i < data.days.length; i += 7) {
    weeks.push(data.days.slice(i, i + 7));
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity Heatmap (Last 90 Days)</CardTitle>
        <p className="text-sm text-muted-foreground">
          Darker = more captures + reviews that day
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <div className="inline-grid gap-1" style={{ gridTemplateColumns: `repeat(${Math.ceil(data.days.length / 7)}, minmax(0, 1fr))` }}>
            {weeks.map((week, weekIndex) => (
              <div key={weekIndex} className="grid grid-rows-7 gap-1">
                {week.map((day, dayIndex) => {
                  const total = day.captures + day.reviews;
                  return (
                    <div
                      key={dayIndex}
                      className={`w-3 h-3 rounded-sm ${getColor(day.captures, day.reviews)}`}
                      title={`${day.date}: ${total} activities (${day.captures} captures, ${day.reviews} reviews)`}
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-4 mt-4 text-xs">
          <span className="text-muted-foreground">Less</span>
          <div className="flex gap-1">
            <div className="w-3 h-3 rounded-sm bg-muted" />
            <div className="w-3 h-3 rounded-sm bg-green-200 dark:bg-green-900" />
            <div className="w-3 h-3 rounded-sm bg-green-400 dark:bg-green-700" />
            <div className="w-3 h-3 rounded-sm bg-green-600 dark:bg-green-500" />
            <div className="w-3 h-3 rounded-sm bg-green-800 dark:bg-green-300" />
          </div>
          <span className="text-muted-foreground">More</span>
        </div>
      </CardContent>
    </Card>
  );
}
