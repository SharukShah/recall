"use client";

import { useDashboardStats } from "@/hooks/useDashboardStats";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatsGrid } from "@/components/dashboard/StatsGrid";
import { ReviewCTA } from "@/components/dashboard/ReviewCTA";
import { StatCard } from "@/components/dashboard/StatCard";
import { RecentCaptures } from "@/components/dashboard/RecentCaptures";
import { SkeletonCard } from "@/components/shared/SkeletonCard";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { BookOpen, HelpCircle } from "lucide-react";

export default function DashboardPage() {
  const { stats, loading, error, refetch } = useDashboardStats();

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="ReCall" />
        <div className="grid grid-cols-2 gap-4">
          <SkeletonCard lines={2} />
          <SkeletonCard lines={2} />
        </div>
        <SkeletonCard lines={3} />
        <SkeletonCard lines={2} />
        <SkeletonCard lines={2} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="ReCall" />
        <ErrorState message="Couldn't load dashboard. Check your connection." onRetry={refetch} />
      </div>
    );
  }

  if (!stats) return null;

  const isNewUser = stats.total_captures === 0;

  if (isNewUser) {
    return (
      <div className="space-y-6">
        <PageHeader title="ReCall" />
        <EmptyState
          message="Welcome! Capture your first learning to get started."
          subMessage="ReCall helps you remember what you learn through spaced repetition."
          cta={{ label: "Capture your first learning", href: "/capture" }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="ReCall" />
      <StatsGrid stats={stats} />
      <ReviewCTA stats={stats} />
      <div className="grid grid-cols-2 gap-4">
        <StatCard value={stats.total_captures} label="captures" icon={BookOpen} />
        <StatCard value={stats.total_questions} label="questions" icon={HelpCircle} />
      </div>
      <RecentCaptures />
    </div>
  );
}
