"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { submitInterviewAnswer, completeInterview } from "@/lib/api";
import type {
  StartInterviewResponse,
  InterviewSummary,
  InterviewQuestion,
  InterviewAnswerResponse,
} from "@/types/api";
import { Loader2, CheckCircle2, XCircle, ArrowRight } from "lucide-react";

interface MockInterviewSessionProps {
  interview: StartInterviewResponse;
  onComplete: (summary: InterviewSummary) => void;
}

export function MockInterviewSession({ interview, onComplete }: MockInterviewSessionProps) {
  const [currentQuestion, setCurrentQuestion] = useState<InterviewQuestion>(interview.first_question);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<InterviewAnswerResponse | null>(null);
  const [followUpAnswer, setFollowUpAnswer] = useState("");
  const [showFollowUp, setShowFollowUp] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const progressPct = (questionNumber / interview.total_questions) * 100;

  const handleSubmit = async () => {
    if (!answer.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await submitInterviewAnswer(
        interview.interview_id,
        currentQuestion.question_order,
        answer
      );
      setFeedback(result);

      if (result.follow_up_question) {
        setShowFollowUp(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit answer");
    } finally {
      setSubmitting(false);
    }
  };

  const handleFollowUpSubmit = async () => {
    if (!followUpAnswer.trim() || !feedback?.follow_up_question) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await submitInterviewAnswer(
        interview.interview_id,
        currentQuestion.question_order,
        followUpAnswer
      );
      setFeedback(result);
      setShowFollowUp(false);
      setFollowUpAnswer("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit follow-up");
    } finally {
      setSubmitting(false);
    }
  };

  const handleNext = () => {
    if (feedback?.done) {
      handleComplete();
      return;
    }

    if (feedback?.next_question) {
      setCurrentQuestion(feedback.next_question);
      setQuestionNumber((n) => n + 1);
      setAnswer("");
      setFeedback(null);
      setShowFollowUp(false);
      setFollowUpAnswer("");
    }
  };

  const handleComplete = async () => {
    setCompleting(true);
    setError(null);
    try {
      const summary = await completeInterview(interview.interview_id);
      onComplete(summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete interview");
      setCompleting(false);
    }
  };

  const scoreColor = (score: number) => {
    if (score >= 4) return "text-green-600";
    if (score >= 3) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Mock Interview</h1>
          <p className="text-sm text-muted-foreground capitalize">
            {interview.topic.replace("_", " ")} • {interview.difficulty} • {interview.duration_minutes} min
          </p>
        </div>
        <Badge variant="outline">
          Q{questionNumber}/{interview.total_questions}
        </Badge>
      </div>

      <Progress value={progressPct} className="h-2" />

      {/* Question */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Question {questionNumber}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-lg leading-relaxed">{currentQuestion.question_text}</p>

          {!feedback ? (
            <>
              <Textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Type your answer here..."
                rows={6}
                className="resize-none"
              />
              <Button
                onClick={handleSubmit}
                disabled={submitting || !answer.trim()}
                className="w-full"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Evaluating...
                  </>
                ) : (
                  "Submit Answer"
                )}
              </Button>
            </>
          ) : (
            <div className="space-y-4">
              {/* Your answer */}
              <div className="rounded-lg bg-muted/50 p-3">
                <p className="text-xs font-medium text-muted-foreground mb-1">Your Answer</p>
                <p className="text-sm">{answer}</p>
              </div>

              {/* Score + Feedback */}
              <div className="flex items-center gap-3">
                <div className={`text-2xl font-bold ${scoreColor(feedback.score)}`}>
                  {feedback.score}/5
                </div>
                {feedback.score >= 4 ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                ) : feedback.score >= 3 ? (
                  <CheckCircle2 className="h-5 w-5 text-yellow-600" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600" />
                )}
              </div>

              <p className="text-sm leading-relaxed">{feedback.feedback}</p>

              {/* Follow-up question */}
              {showFollowUp && feedback.follow_up_question && (
                <div className="border-l-2 border-primary/40 pl-4 space-y-3">
                  <p className="text-sm font-medium">Follow-up: {feedback.follow_up_question}</p>
                  <Textarea
                    value={followUpAnswer}
                    onChange={(e) => setFollowUpAnswer(e.target.value)}
                    placeholder="Your follow-up answer..."
                    rows={4}
                    className="resize-none"
                  />
                  <Button
                    onClick={handleFollowUpSubmit}
                    disabled={submitting || !followUpAnswer.trim()}
                    size="sm"
                  >
                    {submitting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Evaluating...
                      </>
                    ) : (
                      "Submit Follow-up"
                    )}
                  </Button>
                </div>
              )}

              {/* Next / Complete */}
              <Button onClick={handleNext} disabled={completing} className="w-full gap-2">
                {completing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Finishing...
                  </>
                ) : feedback.done ? (
                  "View Results"
                ) : (
                  <>
                    Next Question <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
