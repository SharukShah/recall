"use client";

import { useState, useEffect, useCallback } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SkeletonCard } from "@/components/shared/SkeletonCard";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { CompetencyCoverageGrid } from "@/components/interview/CompetencyCoverageGrid";
import { StarStoryCard } from "@/components/interview/StarStoryCard";
import { BehavioralPracticeModal } from "@/components/interview/BehavioralPracticeModal";
import { Button } from "@/components/ui/button";
import { getBehavioralCoverage, listStories } from "@/lib/api";
import type { BehavioralCoverageResponse, StarStoryListItem } from "@/types/api";
import { Plus, Dumbbell, Loader2 } from "lucide-react";
import Link from "next/link";

export default function BehavioralPrepPage() {
  const [coverage, setCoverage] = useState<BehavioralCoverageResponse | null>(null);
  const [stories, setStories] = useState<StarStoryListItem[]>([]);
  const [storiesTotal, setStoriesTotal] = useState(0);
  const [selectedCompetency, setSelectedCompetency] = useState<string | null>(null);
  const [showPractice, setShowPractice] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cov, storiesData] = await Promise.all([
        getBehavioralCoverage(),
        listStories(selectedCompetency ?? undefined, 20, 0),
      ]);
      setCoverage(cov);
      setStories(storiesData.stories);
      setStoriesTotal(storiesData.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [selectedCompetency]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const loadMoreStories = async () => {
    setLoadingMore(true);
    try {
      const data = await listStories(selectedCompetency ?? undefined, 20, stories.length);
      setStories((prev) => [...prev, ...data.stories]);
      setStoriesTotal(data.total);
    } catch {
      // Silently fail
    } finally {
      setLoadingMore(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Behavioral Prep" />
        <SkeletonCard lines={3} />
        <SkeletonCard lines={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Behavioral Prep" />
        <ErrorState message={error} onRetry={fetchData} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <PageHeader title="Behavioral Prep" />
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setShowPractice(true)} className="gap-1.5">
            <Dumbbell className="h-4 w-4" />
            Practice
          </Button>
          <Link href="/interview/behavioral/new">
            <Button size="sm" className="gap-1.5">
              <Plus className="h-4 w-4" />
              Capture Story
            </Button>
          </Link>
        </div>
      </div>

      {/* Competency Coverage */}
      {coverage && (
        <CompetencyCoverageGrid
          data={coverage}
          selectedCompetency={selectedCompetency}
          onSelect={setSelectedCompetency}
        />
      )}

      {/* Stories List */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium">
          STAR Stories {selectedCompetency && (
            <span className="text-muted-foreground capitalize">
              — {selectedCompetency.replace(/_/g, " ")}
            </span>
          )}
        </h3>
        {stories.length === 0 ? (
          <EmptyState
            message="No stories yet"
            subMessage="Capture behavioral stories to build your interview library."
            cta={{ label: "Capture Story", href: "/interview/behavioral/new" }}
          />
        ) : (
          <>
            <div className="space-y-3">
              {stories.map((story) => (
                <StarStoryCard key={story.id} item={story} onDeleted={fetchData} />
              ))}
            </div>
            {stories.length < storiesTotal && (
              <Button
                variant="ghost"
                size="sm"
                onClick={loadMoreStories}
                disabled={loadingMore}
                className="w-full"
              >
                {loadingMore ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "Load More"
                )}
              </Button>
            )}
          </>
        )}
      </div>

      {/* Practice Modal */}
      {showPractice && (
        <BehavioralPracticeModal
          competency={selectedCompetency ?? undefined}
          onClose={() => setShowPractice(false)}
        />
      )}
    </div>
  );
}
