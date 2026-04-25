"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { useReviewSession } from "@/hooks/useReviewSession";
import { useVoiceReview } from "@/hooks/useVoiceReview";
import { SessionHeader } from "./SessionHeader";
import { ReviewProgressBar } from "./ProgressBar";
import { QuestionCard } from "./QuestionCard";
import { FeedbackCard } from "./FeedbackCard";
import { RatingButtons } from "./RatingButtons";
import { SessionSummary } from "./SessionSummary";
import { EmptyReviewState } from "./EmptyReviewState";
import { VoiceControls } from "./VoiceControls";
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

  const voice = useVoiceReview();

  const answerRef = useRef<HTMLTextAreaElement>(null);
  const feedbackRef = useRef<HTMLDivElement>(null);
  const summaryRef = useRef<HTMLHeadingElement>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const prevPhaseRef = useRef(state.phase);
  const prevIndexRef = useRef(state.currentIndex);

  // Voice: speak question when entering question phase
  useEffect(() => {
    const phaseChanged = prevPhaseRef.current !== state.phase;
    const indexChanged = prevIndexRef.current !== state.currentIndex;
    prevPhaseRef.current = state.phase;
    prevIndexRef.current = state.currentIndex;

    if (state.phase === "question" && (phaseChanged || indexChanged) && currentQuestion) {
      if (voice.voiceEnabled) {
        voice.speak(currentQuestion.question_text);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.phase, state.currentIndex, currentQuestion?.question_id]);

  // Voice: speak feedback when entering feedback phase
  useEffect(() => {
    if (state.phase === "feedback" && state.evaluation && voice.voiceEnabled) {
      const feedbackText = state.evaluation.score === "correct"
        ? state.evaluation.feedback
        : `${state.evaluation.feedback}. The correct answer is: ${state.evaluation.correct_answer}`;
      voice.speak(feedbackText);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.phase, state.evaluation?.feedback]);

  // Voice: auto-listen for answer after question TTS finishes
  // F11: Don't start mic while TTS is playing
  // F10: If already recording, stop instead of starting new
  const handleVoiceAnswer = useCallback(async () => {
    if (!voice.voiceEnabled || state.phase !== "question") return;

    // If already recording, toggle off
    if (voice.isRecording) {
      voice.stopRecording();
      return;
    }

    // Wait for TTS to finish before opening mic
    if (voice.isSpeaking) {
      voice.stopSpeaking();
    }

    const answer = await voice.listenForAnswer();
    if (answer) {
      setAnswer(answer);
    }
  }, [voice, state.phase, setAnswer]);

  // Focus management: move focus on phase transitions
  useEffect(() => {
    if (state.phase === "question") {
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
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <SessionHeader
          currentIndex={state.currentIndex}
          total={state.questions.length}
          onEndSession={handleEndSession}
        />
        <VoiceControls
          voiceEnabled={voice.voiceEnabled}
          isSpeaking={voice.isSpeaking}
          isRecording={voice.isRecording}
          onToggleVoice={voice.toggle}
          onStopSpeaking={voice.stopSpeaking}
        />
      </div>

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
            onVoiceAnswer={voice.voiceEnabled && voice.isSpeechSupported ? handleVoiceAnswer : undefined}
            isRecording={voice.isRecording}
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

      {state.phase === "scheduled" && state.lastSchedule && (
        <div className="flex flex-col items-center gap-3 py-8 animate-crossfade-in">
          <div className="rounded-full bg-primary/10 p-3">
            <svg className="h-6 w-6 text-primary" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-foreground">
            {state.lastSchedule.interval_days < 1
              ? `Next review in ${Math.max(1, Math.round(state.lastSchedule.interval_days * 24 * 60))} min`
              : state.lastSchedule.interval_days < 2
                ? "Next review tomorrow"
                : `Next review in ${Math.round(state.lastSchedule.interval_days)} days`}
          </p>
          <p className="text-xs text-muted-foreground">
            {state.lastSchedule.state_label}
          </p>
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
