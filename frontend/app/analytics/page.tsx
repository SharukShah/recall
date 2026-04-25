"use client";

import { useState, useEffect } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { MasteryDonut } from "@/components/analytics/MasteryDonut";
import { RetentionChart } from "@/components/analytics/RetentionChart";
import { WeakAreasList } from "@/components/analytics/WeakAreasList";
import { VelocityCards } from "@/components/analytics/VelocityCards";
import { ConsistencyStats } from "@/components/analytics/ConsistencyStats";
import { ActivityHeatmap } from "@/components/analytics/ActivityHeatmap";
import { SummaryCards } from "@/components/analytics/SummaryCards";
import { SkeletonCard } from "@/components/shared/SkeletonCard";
import { ErrorState } from "@/components/shared/ErrorState";
import { getAnalytics, getRetentionCurve, getWeakAreas, getActivity } from "@/lib/api";
import type {
  AnalyticsResponse,
  RetentionCurveResponse,
  WeakAreasResponse,
  ActivityResponse,
} from "@/types/analytics";

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [retention, setRetention] = useState<RetentionCurveResponse | null>(null);
  const [weakAreas, setWeakAreas] = useState<WeakAreasResponse | null>(null);
  const [activity, setActivity] = useState<ActivityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [analyticsData, retentionData, weakAreasData, activityData] = await Promise.all([
        getAnalytics(),
        getRetentionCurve(12),
        getWeakAreas(10),
        getActivity(90),
      ]);

      setAnalytics(analyticsData);
      setRetention(retentionData);
      setWeakAreas(weakAreasData);
      setActivity(activityData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Analytics" />
        <SkeletonCard lines={5} />
        <SkeletonCard lines={5} />
      </div>
    );
  }

  if (error || !analytics || !retention || !weakAreas || !activity) {
    return (
      <div className="space-y-6">
        <PageHeader title="Analytics" />
        <ErrorState message={error || "Failed to load data"} onRetry={fetchAllData} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Analytics" />

      <SummaryCards data={analytics.summary} />

      <VelocityCards data={analytics.learning_velocity} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ConsistencyStats data={analytics.review_consistency} />
        <MasteryDonut data={analytics.mastery_distribution} />
      </div>

      <RetentionChart data={retention} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <WeakAreasList data={weakAreas} />
        <ActivityHeatmap data={activity} />
      </div>
    </div>
  );
}
