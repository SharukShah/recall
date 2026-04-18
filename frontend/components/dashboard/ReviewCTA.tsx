import Link from "next/link";
import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { DashboardStats } from "@/types/api";

interface ReviewCTAProps {
  stats: DashboardStats;
}

export function ReviewCTA({ stats }: ReviewCTAProps) {
  return (
    <div className="rounded-lg border border-border p-4 md:p-6 space-y-3">
      <p className="text-lg font-semibold">
        {stats.due_today} {stats.due_today === 1 ? "review" : "reviews"} due today
      </p>
      {stats.due_today > 0 && (
        <Button asChild className="w-full" size="lg">
          <Link href="/review">
            <Play className="mr-2 h-4 w-4" />
            Start Review Session
          </Link>
        </Button>
      )}
      <p className="text-sm text-muted-foreground">
        {stats.reviews_today} reviewed today
      </p>
    </div>
  );
}
