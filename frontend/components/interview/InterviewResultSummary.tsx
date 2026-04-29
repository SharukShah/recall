"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { InterviewSummary } from "@/types/api";
import {
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  ArrowLeft,
} from "lucide-react";
import Link from "next/link";

interface InterviewResultSummaryProps {
  summary: InterviewSummary;
  onBack?: () => void;
}

export function InterviewResultSummary({ summary, onBack }: InterviewResultSummaryProps) {
  const [expandedAnswers, setExpandedAnswers] = useState(false);

  const scoreColor =
    summary.overall_score >= 4
      ? "text-green-600"
      : summary.overall_score >= 3
        ? "text-yellow-600"
        : "text-red-600";

  const scoreBg =
    summary.overall_score >= 4
      ? "bg-green-500"
      : summary.overall_score >= 3
        ? "bg-yellow-500"
        : "bg-red-500";

  const durationMin = summary.duration_seconds
    ? Math.round(summary.duration_seconds / 60)
    : null;

  return (
    <div className="space-y-5 max-w-3xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Interview Results</h1>
        {onBack ? (
          <Button variant="ghost" size="sm" onClick={onBack} className="gap-1">
            <ArrowLeft className="h-4 w-4" /> New Interview
          </Button>
        ) : (
          <Link href="/interview">
            <Button variant="ghost" size="sm" className="gap-1">
              <ArrowLeft className="h-4 w-4" /> Back to Hub
            </Button>
          </Link>
        )}
      </div>

      {/* Score Card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center gap-4">
            {/* Score Circle */}
            <div className="relative h-28 w-28">
              <svg className="h-28 w-28 -rotate-90" viewBox="0 0 100 100">
                <circle
                  cx="50" cy="50" r="40"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="none"
                  className="text-muted/20"
                />
                <circle
                  cx="50" cy="50" r="40"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="none"
                  strokeDasharray={`${(summary.overall_score / 5) * 251.2} 251.2`}
                  strokeLinecap="round"
                  className={scoreColor}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className={`text-2xl font-bold ${scoreColor}`}>
                  {summary.overall_score.toFixed(1)}
                </span>
              </div>
            </div>

            <div className="text-center space-y-1">
              <p className="text-lg font-medium capitalize">
                {summary.topic.replace("_", " ")} • {summary.difficulty}
              </p>
              <div className="flex items-center gap-2 justify-center text-sm text-muted-foreground">
                <span>{summary.total_questions} questions</span>
                {durationMin !== null && <span>• {durationMin} min</span>}
              </div>
            </div>

            {/* Score Breakdown */}
            <div className="flex gap-4 text-center">
              <div>
                <p className="text-lg font-bold text-green-600">{summary.correct_count}</p>
                <p className="text-xs text-muted-foreground">Correct</p>
              </div>
              <div>
                <p className="text-lg font-bold text-yellow-600">{summary.partial_count}</p>
                <p className="text-xs text-muted-foreground">Partial</p>
              </div>
              <div>
                <p className="text-lg font-bold text-red-600">{summary.wrong_count}</p>
                <p className="text-xs text-muted-foreground">Wrong</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Strengths */}
      {summary.strengths.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              Strengths
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {summary.strengths.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
                  {s}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Weaknesses */}
      {summary.weaknesses.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              Areas to Improve
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {summary.weaknesses.map((w, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 shrink-0" />
                  {w}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Tips */}
      {summary.improvement_tips.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-blue-600" />
              Improvement Tips
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {summary.improvement_tips.map((tip, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <Lightbulb className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
                  {tip}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Q&A Breakdown */}
      <Card>
        <CardHeader className="pb-3">
          <button
            onClick={() => setExpandedAnswers(!expandedAnswers)}
            className="flex items-center justify-between w-full"
          >
            <CardTitle className="text-base">Question Details</CardTitle>
            {expandedAnswers ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>
        </CardHeader>
        {expandedAnswers && (
          <CardContent>
            <div className="space-y-4">
              {summary.answers.map((a, i) => (
                <div key={i} className="rounded-lg border p-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium">Q{i + 1}: {a.question_text}</p>
                    {a.score !== null && (
                      <Badge
                        variant={a.score >= 4 ? "default" : a.score >= 3 ? "secondary" : "destructive"}
                        className="shrink-0"
                      >
                        {a.score}/5
                      </Badge>
                    )}
                  </div>
                  {a.user_answer && (
                    <div className="bg-muted/50 rounded p-2">
                      <p className="text-xs font-medium text-muted-foreground mb-1">Your Answer</p>
                      <p className="text-sm">{a.user_answer}</p>
                    </div>
                  )}
                  {a.feedback && (
                    <p className="text-sm text-muted-foreground">{a.feedback}</p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        )}
      </Card>

      <div className="flex gap-3">
        {onBack && (
          <Button onClick={onBack} className="flex-1">
            New Interview
          </Button>
        )}
        <Link href="/interview" className="flex-1">
          <Button variant="outline" className="w-full">
            Back to Hub
          </Button>
        </Link>
      </div>
    </div>
  );
}
