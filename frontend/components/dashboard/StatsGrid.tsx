import { Flame, TrendingUp } from "lucide-react";
import { StatCard } from "./StatCard";
import type { DashboardStats } from "@/types/api";

interface StatsGridProps {
  stats: DashboardStats;
}

export function StatsGrid({ stats }: StatsGridProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <StatCard
        value={stats.streak_days}
        label="day streak"
        icon={Flame}
      />
      <StatCard
        value={`${Math.round(stats.retention_rate)}%`}
        label="retention"
        icon={TrendingUp}
      />
    </div>
  );
}
