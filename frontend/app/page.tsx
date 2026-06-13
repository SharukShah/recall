"use client";

import { useDashboardStats } from "@/hooks/useDashboardStats";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatsGrid } from "@/components/dashboard/StatsGrid";
import { ReviewCTA } from "@/components/dashboard/ReviewCTA";
import { RecentCaptures } from "@/components/dashboard/RecentCaptures";
import { SkeletonCard } from "@/components/shared/SkeletonCard";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { Sunset, GraduationCap, Flame, Plus, Brain } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export default function DashboardPage() {
  const { stats, loading, error, refetch } = useDashboardStats();

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="ReCall" />
        <div className="grid grid-cols-2 gap-3">
          <SkeletonCard lines={2} />
          <SkeletonCard lines={2} />
          <SkeletonCard lines={2} />
          <SkeletonCard lines={2} />
        </div>
        <SkeletonCard lines={3} />
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
      <div className="space-y-8">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold">{getGreeting()} 👋</h1>
          <p className="text-muted-foreground">Let's start building your knowledge base</p>
        </div>
        <EmptyState
          message="Capture your first learning"
          subMessage="Paste notes, speak your thoughts, or import from a URL — ReCall extracts key facts and quizzes you on them."
          cta={{ label: "Start Capturing", href: "/capture" }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Greeting */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{getGreeting()} 👋</h1>
          <p className="text-sm text-muted-foreground">Here's your learning snapshot</p>
        </div>
        <Link href="/capture">
          <Button size="sm" className="gap-1.5">
            <Plus className="h-4 w-4" />
            Capture
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <StatsGrid stats={stats} />

      {/* Review CTA */}
      <ReviewCTA stats={stats} />

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-3">
        {/* Reflection CTA */}
        {!stats.reflection_completed_today ? (
          <Link href="/reflect" className="block">
            <Card className="h-full hover:shadow-md transition-shadow cursor-pointer border-dashed">
              <CardContent className="pt-5 pb-4 flex flex-col items-center gap-2 text-center">
                <div className="rounded-lg bg-orange-50 dark:bg-orange-950/30 p-2">
                  <Sunset className="h-4 w-4 text-orange-500" />
                </div>
                <p className="text-xs font-medium">Reflect</p>
                <p className="text-[10px] text-muted-foreground">
                  {stats.reflection_streak > 0
                    ? `${stats.reflection_streak} day streak 🔥`
                    : "What did you learn?"}
                </p>
              </CardContent>
            </Card>
          </Link>
        ) : (
          <Card className="h-full opacity-60">
            <CardContent className="pt-5 pb-4 flex flex-col items-center gap-2 text-center">
              <div className="rounded-lg bg-green-50 dark:bg-green-950/30 p-2">
                <Flame className="h-4 w-4 text-green-500" />
              </div>
              <p className="text-xs font-medium">Reflected ✓</p>
              <p className="text-[10px] text-muted-foreground">{stats.reflection_streak} day streak</p>
            </CardContent>
          </Card>
        )}

        {/* Teach session */}
        <Link href="/teach" className="block">
          <Card className="h-full hover:shadow-md transition-shadow cursor-pointer border-dashed">
            <CardContent className="pt-5 pb-4 flex flex-col items-center gap-2 text-center">
              <div className="rounded-lg bg-purple-50 dark:bg-purple-950/30 p-2">
                <GraduationCap className="h-4 w-4 text-purple-500" />
              </div>
              <p className="text-xs font-medium">
                {stats.active_teach_session ? "Resume Lesson" : "Learn a Topic"}
              </p>
              <p className="text-[10px] text-muted-foreground">
                {stats.active_teach_session ? "In progress" : "AI teaches you"}
              </p>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Recent Captures */}
      <RecentCaptures />
    </div>
  );
}
