"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listCaptures } from "@/lib/api";
import type { CaptureListItem } from "@/types/api";
import { truncateText, formatRelativeDate } from "@/lib/utils";
import { SkeletonCard } from "@/components/shared/SkeletonCard";
import { ChevronRight } from "lucide-react";

export function RecentCaptures() {
  const [captures, setCaptures] = useState<CaptureListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listCaptures(5, 0)
      .then(setCaptures)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Recent Captures</h2>
        <SkeletonCard lines={2} />
        <SkeletonCard lines={2} />
      </div>
    );
  }

  if (captures.length === 0) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Recent Captures</h2>
        <Link href="/history" className="text-xs text-primary hover:underline">View all →</Link>
      </div>
      <div className="space-y-2">
        {captures.map((capture) => (
          <Link
            key={capture.id}
            href={`/history/${capture.id}`}
            className="group flex items-center gap-3 rounded-xl border border-border bg-card p-3 md:p-4 hover:border-primary/30 hover:shadow-sm transition-all"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {truncateText(capture.raw_text, 100)}
              </p>
              <div className="flex items-center gap-2 mt-1.5 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5">{capture.facts_count} facts</span>
                <span>·</span>
                <span>{formatRelativeDate(capture.created_at)}</span>
              </div>
            </div>
            <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
          </Link>
        ))}
      </div>
    </div>
  );
}
