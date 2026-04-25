import { Flame, TrendingUp, BookOpen, HelpCircle } from "lucide-react";
import { StatCard } from "./StatCard";
import type { DashboardStats } from "@/types/api";

interface StatsGridProps {
  stats: DashboardStats;
}

export function StatsGrid({ stats }: StatsGridProps) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard
        value={stats.streak_days}
        label="Day Streak"
        icon={Flame}
        trend={stats.streak_days > 0 ? "Keep it going!" : "Start today"}
      />
      <StatCard
        value={`${Math.round(stats.retention_rate)}%`}
        label="Retention Rate"
        icon={TrendingUp}
        trend={stats.retention_rate >= 80 ? "Great recall" : stats.retention_rate >= 50 ? "Getting better" : "Keep practicing"}
      />
      <StatCard
        value={stats.total_captures}
        label="Captures"
        icon={BookOpen}
      />
      <StatCard
        value={stats.total_questions}
        label="Questions"
        icon={HelpCircle}
      />
    </div>
  );
}
