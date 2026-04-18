"use client";

import { useRef, useEffect, useState } from "react";
import { useReviewSession } from "@/hooks/useReviewSession";
import { SessionHeader } from "./SessionHeader";
import { ReviewProgressBar } from "./ProgressBar";
import { QuestionCard } from "./QuestionCard";
import { FeedbackCard } from "./FeedbackCard";
import { RatingButtons } from "./RatingButtons";
import { SessionSummary } from "./SessionSummary";
import { EmptyReviewState } from "./EmptyReviewState";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { ErrorState } from "@/components/shared/ErrorState";

export function ReviewSession() {
  const {
    state,
    currentQuestion,
    setAnswer,
    checkAnswer,
    submitRating,
    endSession,
    retryLoad,
  } = useReviewSession();

  const answerRef = useRef<HTMLTextAreaElement>(null);
  const feedbackRef = useRef<HTMLDivElement>(null);
  const summaryRef = useRef<HTMLHeadingElement>(null);
  const [showConfirm, setShowConfirm] = useState(false);

  // Focus management: move focus on phase transitions
  useEffect(() => {
    if (state.phase === "question") {
      // Small delay for DOM to update
      setTimeout(() => answerRef.current?.focus(), 100);
    } else if (state.phase === "feedback") {
      setTimeout(() => feedbackRef.current?.focus(), 100);
    } else if (state.phase === "complete" && state.sessionStats.answered > 0) {
      setTimeout(() => summaryRef.current?.focus(), 100);
    }
  }, [state.phase, state.currentIndex, state.sessionStats.answered]);

  const handleEndSession = () => {
    if (state.sessionStats.answered > 0 && state.sessionStats.answered < state.questions.length) {
      setShowConfirm(true);
    } else {
      endSession();
    }
  };

  if (state.phase === "loading") {
    return <LoadingSpinner message="Loading review questions..." />;
  }

  if (state.error && state.questions.length === 0) {
    return <ErrorState message={state.error} onRetry={retryLoad} />;
  }

  if (state.phase === "complete" && state.sessionStats.answered === 0 && state.questions.length === 0) {
    return <EmptyReviewState />;
  }

  if (state.phase === "complete") {
    return <SessionSummary stats={state.sessionStats} headingRef={summaryRef} />;
  }

  if (!currentQuestion) {
    return <EmptyReviewState />;
  }

  return (
    <div className="space-y-6">
      <SessionHeader
        currentIndex={state.currentIndex}
        total={state.questions.length}
        onEndSession={handleEndSession}
      />

      <ReviewProgressBar
        current={state.sessionStats.answered}
        total={state.questions.length}
      />

      {(state.phase === "question" || state.phase === "evaluating") && (
        <div className="animate-slide-in-left" key={`q-${state.currentIndex}`}>
          <QuestionCard
            question={currentQuestion}
            answer={state.currentAnswer}
            onAnswerChange={setAnswer}
            onCheckAnswer={checkAnswer}
            isEvaluating={state.phase === "evaluating"}
            answerRef={answerRef}
          />
        </div>
      )}

      {(state.phase === "feedback" || state.phase === "rating") && state.evaluation && (
        <div className="space-y-6 animate-crossfade-in" ref={feedbackRef} tabIndex={-1}>
          <FeedbackCard evaluation={state.evaluation} />
          <RatingButtons
            suggestedRating={state.evaluation.suggested_rating}
            onRate={submitRating}
            disabled={state.phase === "rating"}
          />
        </div>
      )}

      {state.phase === "feedback" && !state.evaluation && state.error && (
        <div className="space-y-6 animate-crossfade-in" ref={feedbackRef} tabIndex={-1}>
          <div className="rounded-lg border border-yellow-200 dark:border-yellow-800 p-4 text-sm text-yellow-800 dark:text-yellow-200">
            Evaluation failed — rate this one yourself based on how well you think you knew the answer.
          </div>
          <RatingButtons
            onRate={submitRating}
            disabled={false}
          />
        </div>
      )}

      {/* End Session confirmation dialog */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 animate-crossfade-in">
          <div className="bg-card border rounded-lg p-6 max-w-sm mx-4 space-y-4 shadow-md">
            <h3 className="text-lg font-semibold">End session?</h3>
            <p className="text-sm text-muted-foreground">
              You&apos;ve reviewed {state.sessionStats.answered} of {state.questions.length} questions.
              Remaining questions will stay in your review queue.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 text-sm rounded-md border hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => { setShowConfirm(false); endSession(); }}
                className="px-4 py-2 text-sm rounded-md bg-destructive text-destructive-foreground hover:opacity-90 transition-colors"
              >
                End Session
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
