"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listCaptures } from "@/lib/api";
import type { CaptureListItem } from "@/types/api";
import { truncateText, formatRelativeDate } from "@/lib/utils";
import { SkeletonCard } from "@/components/shared/SkeletonCard";

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
        <h2 className="text-lg font-semibold">Recent Captures</h2>
        <SkeletonCard lines={2} />
        <SkeletonCard lines={2} />
      </div>
    );
  }

  if (captures.length === 0) return null;

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Recent Captures</h2>
      <div className="space-y-2">
        {captures.map((capture) => (
          <Link
            key={capture.id}
            href={`/history/${capture.id}`}
            className="block rounded-lg border border-border p-3 md:p-4 hover:bg-accent transition-colors"
          >
            <p className="text-sm font-medium">
              {truncateText(capture.raw_text, 120)}
            </p>
            <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
              <span>{capture.facts_count} facts</span>
              <span>·</span>
              <span>{formatRelativeDate(capture.created_at)}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
