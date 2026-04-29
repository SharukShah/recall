"use client";

import { useState, useEffect } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SkeletonCard } from "@/components/shared/SkeletonCard";
import { ErrorState } from "@/components/shared/ErrorState";
import { InterviewResultSummary } from "@/components/interview/InterviewResultSummary";
import { getInterviewSummary } from "@/lib/api";
import type { InterviewSummary } from "@/types/api";
import { use } from "react";

export default function InterviewResultsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [summary, setSummary] = useState<InterviewSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getInterviewSummary(id);
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load results");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Interview Results" />
        <SkeletonCard lines={5} />
        <SkeletonCard lines={3} />
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="space-y-6">
        <PageHeader title="Interview Results" />
        <ErrorState message={error || "Results not found"} onRetry={fetchSummary} />
      </div>
    );
  }

  return <InterviewResultSummary summary={summary} />;
}
