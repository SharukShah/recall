"use client";

import { useState, useEffect, useCallback } from "react";
import { listCaptures } from "@/lib/api";
import type { CaptureListItem } from "@/types/api";
import { CaptureCard } from "./CaptureCard";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { Button } from "@/components/ui/button";

const PAGE_SIZE = 20;

export function CaptureList() {
  const [captures, setCaptures] = useState<CaptureListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);

  const load = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);
      const data = await listCaptures(PAGE_SIZE, 0);
      setCaptures(data);
      setHasMore(data.length === PAGE_SIZE);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load captures");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const loadMore = async () => {
    setLoadingMore(true);
    try {
      const data = await listCaptures(PAGE_SIZE, captures.length);
      setCaptures((prev) => [...prev, ...data]);
      setHasMore(data.length === PAGE_SIZE);
    } catch {
      // Silently fail on load more
    } finally {
      setLoadingMore(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading captures..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (captures.length === 0) {
    return (
      <EmptyState
        message="No captures yet"
        subMessage="Start by capturing something you learned!"
        cta={{ label: "Capture Knowledge", href: "/capture" }}
      />
    );
  }

  return (
    <div className="space-y-3">
      {captures.map((capture) => (
        <CaptureCard key={capture.id} capture={capture} />
      ))}
      {hasMore && (
        <div className="flex justify-center pt-4">
          <Button variant="outline" onClick={loadMore} disabled={loadingMore}>
            {loadingMore ? "Loading..." : "Load more"}
          </Button>
        </div>
      )}
    </div>
  );
}
