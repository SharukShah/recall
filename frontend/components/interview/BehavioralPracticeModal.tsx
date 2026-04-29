"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { getPracticeQuestion, evaluateBehavioral } from "@/lib/api";
import type { PracticeQuestionResponse, BehavioralEvaluation } from "@/types/api";
import { X, Loader2, Lightbulb, RefreshCw } from "lucide-react";

interface BehavioralPracticeModalProps {
  competency?: string;
  onClose: () => void;
}

export function BehavioralPracticeModal({ competency, onClose }: BehavioralPracticeModalProps) {
  const [question, setQuestion] = useState<PracticeQuestionResponse | null>(null);
  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState<BehavioralEvaluation | null>(null);
  const [loadingQuestion, setLoadingQuestion] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchQuestion = async () => {
    setLoadingQuestion(true);
    setError(null);
    setEvaluation(null);
    setAnswer("");
    try {
      const data = await getPracticeQuestion(competency);
      setQuestion(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get question");
    } finally {
      setLoadingQuestion(false);
    }
  };

  const handleEvaluate = async () => {
    if (!question || !answer.trim()) return;
    setEvaluating(true);
    setError(null);
    try {
      const result = await evaluateBehavioral(question.competency, question.question, answer);
      setEvaluation(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to evaluate");
    } finally {
      setEvaluating(false);
    }
  };

  // Load first question on mount
  if (!question && !loadingQuestion && !error) {
    fetchQuestion();
  }

  const scoreLabel = (score: number) => {
    if (score >= 4) return "text-green-600";
    if (score >= 3) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-background border rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Behavioral Practice</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-4 space-y-4">
          {loadingQuestion ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : error && !question ? (
            <div className="text-center py-8 space-y-2">
              <p className="text-sm text-destructive">{error}</p>
              <Button size="sm" variant="outline" onClick={fetchQuestion}>Retry</Button>
            </div>
          ) : question ? (
            <>
              {/* Question */}
              <div>
                <Badge variant="secondary" className="mb-2 capitalize">
                  {question.competency.replace(/_/g, " ")}
                </Badge>
                <p className="text-base font-medium leading-relaxed">{question.question}</p>
              </div>

              {/* Tips */}
              <div className="rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900 p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Lightbulb className="h-4 w-4 text-blue-600" />
                  <span className="text-xs font-medium text-blue-600">Tips</span>
                </div>
                <p className="text-sm text-blue-800 dark:text-blue-300">{question.tips}</p>
              </div>

              {!evaluation ? (
                <>
                  {/* Answer input */}
                  <Textarea
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Use the STAR framework: Situation, Task, Action, Result..."
                    rows={8}
                    className="resize-none"
                  />

                  {error && <p className="text-sm text-destructive">{error}</p>}

                  <Button
                    onClick={handleEvaluate}
                    disabled={evaluating || !answer.trim()}
                    className="w-full"
                  >
                    {evaluating ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Evaluating...
                      </>
                    ) : (
                      "Evaluate My Answer"
                    )}
                  </Button>
                </>
              ) : (
                <>
                  {/* STAR Scores */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Overall Score</span>
                      <span className={`text-lg font-bold ${scoreLabel(evaluation.overall_score)}`}>
                        {evaluation.overall_score}/5
                      </span>
                    </div>
                    {[
                      { label: "Situation", score: evaluation.situation_score },
                      { label: "Task", score: evaluation.task_score },
                      { label: "Action", score: evaluation.action_score },
                      { label: "Result", score: evaluation.result_score },
                    ].map((item) => (
                      <div key={item.label} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span>{item.label}</span>
                          <span className={scoreLabel(item.score)}>{item.score}/5</span>
                        </div>
                        <Progress value={(item.score / 5) * 100} className="h-1.5" />
                      </div>
                    ))}
                  </div>

                  {/* Feedback */}
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-sm leading-relaxed">{evaluation.feedback}</p>
                  </div>

                  {/* Suggestions */}
                  {evaluation.suggestions.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-xs font-medium text-muted-foreground">Suggestions</p>
                      <ul className="space-y-1">
                        {evaluation.suggestions.map((s, i) => (
                          <li key={i} className="text-sm flex items-start gap-2">
                            <span className="text-primary mt-0.5">•</span>
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <Button onClick={fetchQuestion} variant="outline" className="w-full gap-2">
                    <RefreshCw className="h-4 w-4" />
                    Next Question
                  </Button>
                </>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
