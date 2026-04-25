import Link from "next/link";
import { Play, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { DashboardStats } from "@/types/api";

interface ReviewCTAProps {
  stats: DashboardStats;
}

export function ReviewCTA({ stats }: ReviewCTAProps) {
  if (stats.due_today === 0) {
    return (
      <div className="rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/30 p-4 md:p-5">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-green-100 dark:bg-green-900/50 p-2">
            <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-green-800 dark:text-green-200">All caught up!</p>
            <p className="text-xs text-green-600 dark:text-green-400">{stats.reviews_today} reviewed today</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border-2 border-primary/20 bg-primary/5 p-4 md:p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-lg font-bold">
            {stats.due_today} {stats.due_today === 1 ? "review" : "reviews"} due
          </p>
          <p className="text-xs text-muted-foreground">{stats.reviews_today} completed today</p>
        </div>
        <div className="text-3xl font-bold text-primary">{stats.due_today}</div>
      </div>
      <Button asChild className="w-full" size="lg">
        <Link href="/review">
          <Play className="mr-2 h-4 w-4" />
          Start Review Session
        </Link>
      </Button>
    </div>
  );
}
