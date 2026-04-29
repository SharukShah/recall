"use client";

import { useState, useEffect } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SkeletonCard } from "@/components/shared/SkeletonCard";
import { ErrorState } from "@/components/shared/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import Link from "next/link";
import {
  Brain,
  BarChart3,
  AlertTriangle,
  Flame,
  Users,
  Clock,
  Trophy,
  ArrowRight,
} from "lucide-react";
import {
  getTopicCoverage,
  getWeakCategories,
  getStreakInfo,
  getBehavioralCoverage,
  listInterviews,
} from "@/lib/api";
import type {
  TopicCoverageResponse,
  WeakCategoriesResponse,
  StreakInfoResponse,
  BehavioralCoverageResponse,
  InterviewListResponse,
} from "@/types/api";

export default function InterviewPrepPage() {
  const [topicCoverage, setTopicCoverage] = useState<TopicCoverageResponse | null>(null);
  const [weakCategories, setWeakCategories] = useState<WeakCategoriesResponse | null>(null);
  const [streakInfo, setStreakInfo] = useState<StreakInfoResponse | null>(null);
  const [behavioral, setBehavioral] = useState<BehavioralCoverageResponse | null>(null);
  const [recentInterviews, setRecentInterviews] = useState<InterviewListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [tc, wc, si, bc, ri] = await Promise.all([
        getTopicCoverage().catch(() => null),
        getWeakCategories().catch(() => null),
        getStreakInfo().catch(() => null),
        getBehavioralCoverage().catch(() => null),
        listInterviews(undefined, 5, 0).catch(() => null),
      ]);
      setTopicCoverage(tc);
      setWeakCategories(wc);
      setStreakInfo(si);
      setBehavioral(bc);
      setRecentInterviews(ri);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Interview Prep" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SkeletonCard lines={4} />
          <SkeletonCard lines={4} />
          <SkeletonCard lines={4} />
          <SkeletonCard lines={4} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Interview Prep" />
        <ErrorState message={error} onRetry={fetchAll} />
      </div>
    );
  }

  const totalCategories = topicCoverage?.categories.length ?? 0;
  const masteredCategories = topicCoverage?.categories.filter(
    (c) => c.total_questions > 0 && c.mastered_count / c.total_questions > 0.8
  ).length ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader title="Interview Prep" />
        <Link href="/interview/history">
          <Button variant="outline" size="sm" className="gap-1.5">
            <Clock className="h-4 w-4" />
            History
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Mock Interview Card */}
        <Link href="/interview/mock" className="block">
          <Card className="h-full hover:shadow-md transition-shadow cursor-pointer border-primary/20 hover:border-primary/40">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-primary/10 p-2.5">
                  <Brain className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-base">Mock Interview</CardTitle>
                  <p className="text-sm text-muted-foreground">Practice with AI interviewer</p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {recentInterviews && recentInterviews.interviews.length > 0 ? (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">Recent:</p>
                  {recentInterviews.interviews.slice(0, 2).map((iv) => (
                    <div key={iv.id} className="flex items-center justify-between text-sm">
                      <span className="capitalize">{iv.topic.replace("_", " ")}</span>
                      <Badge variant={
                        iv.overall_score !== null && iv.overall_score >= 4 ? "default" :
                        iv.overall_score !== null && iv.overall_score >= 3 ? "secondary" : "destructive"
                      }>
                        {iv.overall_score !== null ? `${iv.overall_score.toFixed(1)}/5` : "In Progress"}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Start your first mock interview</p>
              )}
              <div className="flex items-center gap-1 text-primary text-sm font-medium mt-3">
                Start Interview <ArrowRight className="h-4 w-4" />
              </div>
            </CardContent>
          </Card>
        </Link>

        {/* Topic Coverage Card */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-blue-500/10 p-2.5">
                <BarChart3 className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <CardTitle className="text-base">Topic Coverage</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {masteredCategories}/{totalCategories} categories mastered
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {topicCoverage && topicCoverage.categories.length > 0 ? (
              <div className="space-y-2">
                {topicCoverage.categories.slice(0, 4).map((cat) => {
                  const pct = cat.total_questions > 0
                    ? Math.round((cat.mastered_count / cat.total_questions) * 100)
                    : 0;
                  return (
                    <div key={cat.category} className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="capitalize">{cat.category.replace("_", " ")}</span>
                        <span className="text-muted-foreground">{pct}%</span>
                      </div>
                      <Progress value={pct} className="h-1.5" />
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No topics tracked yet</p>
            )}
          </CardContent>
        </Card>

        {/* Weak Areas Card */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-amber-500/10 p-2.5">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
              </div>
              <div>
                <CardTitle className="text-base">Weak Areas</CardTitle>
                <p className="text-sm text-muted-foreground">Focus on these topics</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {weakCategories && weakCategories.weak_categories.length > 0 ? (
              <div className="space-y-3">
                {weakCategories.weak_categories.slice(0, 3).map((wc) => (
                  <div key={wc.category} className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium capitalize">{wc.category.replace("_", " ")}</p>
                      <p className="text-xs text-muted-foreground">
                        {Math.round(wc.avg_retention * 100)}% retention
                      </p>
                    </div>
                    <Link href={`/review?categories=${encodeURIComponent(wc.category)}`}>
                      <Button size="sm" variant="outline">Practice</Button>
                    </Link>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No weak areas detected</p>
            )}
          </CardContent>
        </Card>

        {/* Streak Progress Card */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-orange-500/10 p-2.5">
                <Flame className="h-5 w-5 text-orange-500" />
              </div>
              <div className="flex items-center gap-2">
                <CardTitle className="text-base">Streak Progress</CardTitle>
                {streakInfo?.streak_at_risk && (
                  <Badge variant="destructive" className="text-[10px] px-1.5 py-0">At Risk!</Badge>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {streakInfo ? (
              <div className="space-y-3">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold">{streakInfo.current_streak}</span>
                  <span className="text-sm text-muted-foreground">day streak</span>
                </div>
                {streakInfo.next_milestone !== null && (
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Next: {streakInfo.next_milestone}-day milestone</span>
                      <span>{streakInfo.days_to_milestone} days to go</span>
                    </div>
                    <Progress
                      value={streakInfo.next_milestone > 0
                        ? (streakInfo.current_streak / streakInfo.next_milestone) * 100
                        : 0}
                      className="h-2"
                    />
                  </div>
                )}
                {streakInfo.milestones_achieved.length > 0 && (
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Trophy className="h-3 w-3" />
                    {streakInfo.milestones_achieved.length} milestones achieved
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Start a streak by reviewing daily</p>
            )}
          </CardContent>
        </Card>

        {/* Behavioral Prep Card */}
        <Link href="/interview/behavioral" className="block md:col-span-2">
          <Card className="h-full hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-purple-500/10 p-2.5">
                  <Users className="h-5 w-5 text-purple-500" />
                </div>
                <div>
                  <CardTitle className="text-base">Behavioral Prep</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    {behavioral
                      ? `${behavioral.covered_competencies}/${behavioral.total_competencies} competencies covered`
                      : "Build your STAR story library"}
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {behavioral && behavioral.competencies.length > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {behavioral.competencies.slice(0, 8).map((comp) => (
                    <div
                      key={comp.competency}
                      className={`rounded-lg border p-2 text-center text-xs ${
                        comp.story_count > 0
                          ? "border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/30"
                          : "border-border bg-muted/30"
                      }`}
                    >
                      <p className="font-medium capitalize truncate">{comp.competency.replace("_", " ")}</p>
                      <p className="text-muted-foreground">{comp.story_count} stories</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No stories captured yet — start building your library</p>
              )}
              <div className="flex items-center gap-1 text-primary text-sm font-medium mt-3">
                View Behavioral Prep <ArrowRight className="h-4 w-4" />
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
