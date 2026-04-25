"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { LearningVelocity } from "@/types/analytics";

interface VelocityCardsProps {
  data: LearningVelocity;
}

function VelocityCard({
  title,
  thisWeek,
  lastWeek,
}: {
  title: string;
  thisWeek: number;
  lastWeek: number;
}) {
  const diff = thisWeek - lastWeek;
  const percentage =
    lastWeek > 0 ? ((diff / lastWeek) * 100).toFixed(0) : thisWeek > 0 ? "∞" : "0";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold">{thisWeek}</span>
          <span className="text-sm text-muted-foreground">this week</span>
        </div>
        <div className="flex items-center gap-2 mt-2 text-sm">
          {diff > 0 ? (
            <>
              <TrendingUp className="h-4 w-4 text-green-600" />
              <span className="text-green-600 font-semibold">+{percentage}%</span>
            </>
          ) : diff < 0 ? (
            <>
              <TrendingDown className="h-4 w-4 text-red-600" />
              <span className="text-red-600 font-semibold">{percentage}%</span>
            </>
          ) : (
            <>
              <Minus className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">No change</span>
            </>
          )}
          <span className="text-muted-foreground">vs last week ({lastWeek})</span>
        </div>
      </CardContent>
    </Card>
  );
}

export function VelocityCards({ data }: VelocityCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <VelocityCard
        title="Captures"
        thisWeek={data.captures_this_week}
        lastWeek={data.captures_last_week}
      />
      <VelocityCard
        title="Reviews"
        thisWeek={data.reviews_this_week}
        lastWeek={data.reviews_last_week}
      />
      <VelocityCard
        title="Questions Generated"
        thisWeek={data.questions_generated_this_week}
        lastWeek={0}
      />
    </div>
  );
}
