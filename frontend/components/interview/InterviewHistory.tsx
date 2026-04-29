"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { listInterviews } from "@/lib/api";
import type { InterviewListItem } from "@/types/api";
import { SkeletonCard } from "@/components/shared/SkeletonCard";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { Clock, Loader2 } from "lucide-react";
import Link from "next/link";

export function InterviewHistory() {
  const [interviews, setInterviews] = useState<InterviewListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = 10;

  const fetchInterviews = async (reset = false) => {
    const isInitial = reset;
    if (isInitial) {
      setLoading(true);
    } else {
      setLoadingMore(true);
    }
    setError(null);
    try {
      const newOffset = reset ? 0 : offset;
      const data = await listInterviews(undefined, limit, newOffset);
      if (reset) {
        setInterviews(data.interviews);
        setOffset(limit);
      } else {
        setInterviews((prev) => [...prev, ...data.interviews]);
        setOffset((prev) => prev + limit);
      }
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load interviews");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    fetchInterviews(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <SkeletonCard lines={5} />;
  if (error) return <ErrorState message={error} onRetry={() => fetchInterviews(true)} />;
  if (interviews.length === 0) {
    return (
      <EmptyState
        message="No interviews yet"
        subMessage="Start a mock interview to practice and track your progress."
        cta={{ label: "Start Interview", href: "/interview/mock" }}
      />
    );
  }

  const scoreBadge = (score: number | null) => {
    if (score === null) return <Badge variant="secondary">In Progress</Badge>;
    if (score >= 4) return <Badge className="bg-green-600">{score.toFixed(1)}/5</Badge>;
    if (score >= 3) return <Badge className="bg-yellow-600">{score.toFixed(1)}/5</Badge>;
    return <Badge variant="destructive">{score.toFixed(1)}/5</Badge>;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Clock className="h-4 w-4" />
          Interview History
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {interviews.map((iv) => (
            <Link key={iv.id} href={`/interview/results/${iv.id}`} className="block">
              <div className="flex items-center justify-between rounded-lg border p-3 hover:bg-accent transition-colors">
                <div className="space-y-1">
                  <p className="text-sm font-medium capitalize">
                    {iv.topic.replace("_", " ")}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="capitalize">{iv.difficulty}</span>
                    <span>•</span>
                    <span>{iv.total_questions} questions</span>
                    <span>•</span>
                    <span>{new Date(iv.started_at).toLocaleDateString()}</span>
                  </div>
                </div>
                {scoreBadge(iv.overall_score)}
              </div>
            </Link>
          ))}
        </div>

        {interviews.length < total && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fetchInterviews(false)}
            disabled={loadingMore}
            className="w-full mt-3"
          >
            {loadingMore ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Load More"
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
