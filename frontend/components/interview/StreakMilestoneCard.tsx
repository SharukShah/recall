"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { StreakInfoResponse } from "@/types/api";
import { Flame, Trophy } from "lucide-react";

interface StreakMilestoneCardProps {
  data: StreakInfoResponse;
}

export function StreakMilestoneCard({ data }: StreakMilestoneCardProps) {
  const progressPct =
    data.next_milestone !== null && data.next_milestone > 0
      ? Math.min((data.current_streak / data.next_milestone) * 100, 100)
      : 100;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Flame className="h-4 w-4 text-orange-500" />
            Streak Progress
          </CardTitle>
          {data.streak_at_risk && (
            <Badge variant="destructive" className="text-xs">At Risk!</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Current streak */}
        <div className="text-center">
          <p className="text-4xl font-bold">{data.current_streak}</p>
          <p className="text-sm text-muted-foreground">day streak</p>
          {data.longest_streak > data.current_streak && (
            <p className="text-xs text-muted-foreground mt-1">
              Longest: {data.longest_streak} days
            </p>
          )}
        </div>

        {/* Milestone progress */}
        {data.next_milestone !== null && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">
                Next: {data.next_milestone}-day milestone
              </span>
              {data.days_to_milestone !== null && (
                <span className="font-medium">{data.days_to_milestone} days to go</span>
              )}
            </div>
            <Progress value={progressPct} className="h-2.5" />
          </div>
        )}

        {/* Achieved milestones */}
        {data.milestones_achieved.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Milestones Achieved
            </p>
            <div className="space-y-1.5">
              {data.milestones_achieved.map((m) => (
                <div key={m.milestone} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <Trophy className="h-3.5 w-3.5 text-yellow-500" />
                    <span>{m.milestone}-day streak</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(m.achieved_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
