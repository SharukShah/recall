"use client";

import { useCallback, useState, useEffect } from "react";
import { useVoiceAgent } from "@/hooks/useVoiceAgent";
import { VoiceOrb } from "@/components/voice/VoiceOrb";
import { VoiceTranscript } from "@/components/voice/VoiceTranscript";
import { VoiceProgress } from "@/components/voice/VoiceProgress";
import { VoiceReviewQueue, type VoiceReviewItem } from "@/components/voice/VoiceReviewQueue";
import { Button } from "@/components/ui/button";

const SUGGESTION_CHIPS = [
  { label: "Quiz me", icon: "🧠" },
  { label: "Capture something", icon: "💡" },
  { label: "Teach me a topic", icon: "📚" },
  { label: "How am I doing?", icon: "📊" },
];

export default function VoicePage() {
  const {
    status,
    isAgentSpeaking,
    isUserSpeaking,
    transcript,
    error,
    sessionDuration,
    lastFunctionResult,
    sessionSummary,
    connect,
    disconnect,
  } = useVoiceAgent();

  const isActive = status === "active" || status === "ready";
  const isConnecting = status === "connecting";

  // Track voice review queue state
  const [reviewQueue, setReviewQueue] = useState<VoiceReviewItem[]>([]);
  const [reviewCurrent, setReviewCurrent] = useState(0);
  const [reviewTotal, setReviewTotal] = useState(0);
  const [reviewActive, setReviewActive] = useState(false);

  useEffect(() => {
    if (!lastFunctionResult) return;
    const { name, result: r } = lastFunctionResult;

    if (name === "start_review_session") {
      const due = (r.due_count as number) || 0;
      if (due > 0 && r.first_question) {
        const fq = r.first_question as Record<string, unknown>;
        const first: VoiceReviewItem = {
          question_id: (fq.question_id as string) || "q-1",
          question_text: (fq.question_text as string) || "",
          question_type: (fq.question_type as string) || "recall",
          question_number: 1,
        };
        const upcoming = ((r.upcoming_questions || r.questions) as Array<Record<string, unknown>>) || [];
        const items: VoiceReviewItem[] = [
          first,
          ...upcoming.slice(0, 3).map((q, i) => ({
            question_id: (q.question_id as string) || `q-${i + 2}`,
            question_text: (q.question_text as string) || "",
            question_type: (q.question_type as string) || "recall",
            question_number: i + 2,
          })),
        ];
        setReviewQueue(items);
        setReviewCurrent(1);
        setReviewTotal(due);
        setReviewActive(true);
      } else {
        setReviewActive(false);
        setReviewQueue([]);
      }
    } else if (name === "get_next_question") {
      const qNum = (r.question_number as number) || 0;
      const total = (r.total_questions as number) || reviewTotal;
      setReviewCurrent(qNum);
      setReviewTotal(total);

      if (r.done) {
        setReviewActive(false);
        setReviewQueue([]);
      } else if (r.question_text) {
        setReviewQueue((prev) => {
          const exists = prev.some((item) => item.question_number === qNum);
          if (!exists) {
            return [
              ...prev,
              {
                question_id: (r.question_id as string) || `q-${qNum}`,
                question_text: (r.question_text as string) || "",
                question_type: (r.question_type as string) || "recall",
                question_number: qNum,
              },
            ];
          }
          return prev;
        });
      }
    }
  }, [lastFunctionResult, reviewTotal]);

  // Reset queue when session ends
  useEffect(() => {
    if (!isActive) {
      setReviewActive(false);
      setReviewQueue([]);
    }
  }, [isActive]);

  const orbState = isActive
    ? isAgentSpeaking
      ? "speaking"
      : isUserSpeaking
        ? "listening"
        : "listening"
    : isConnecting
      ? "thinking"
      : "idle";

  const handleStart = useCallback(async () => {
    await connect();
  }, [connect]);

  const handleEnd = useCallback(() => {
    disconnect();
  }, [disconnect]);

  // Derive active workflow from last function result
  const activeWorkflow = lastFunctionResult
    ? lastFunctionResult.name.includes("review") || lastFunctionResult.name.includes("question") || lastFunctionResult.name.includes("evaluate") || lastFunctionResult.name.includes("rate")
      ? "review"
      : lastFunctionResult.name.includes("teach") || lastFunctionResult.name.includes("chunk")
        ? "teach"
        : lastFunctionResult.name.includes("capture") || lastFunctionResult.name === "finish_capture"
          ? "capture"
          : null
    : null;

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold">ReCall</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Your personal study companion
        </p>
      </div>

      {/* Suggestion chips — shown when idle */}
      {!isActive && !isConnecting && !sessionSummary && (
        <div className="flex flex-wrap justify-center gap-2 max-w-sm">
          {SUGGESTION_CHIPS.map((chip) => (
            <span
              key={chip.label}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/50 px-3 py-1.5 text-xs text-muted-foreground"
            >
              <span>{chip.icon}</span>
              {chip.label}
            </span>
          ))}
        </div>
      )}

      {/* Active workflow indicator */}
      {isActive && activeWorkflow && (
        <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
          {activeWorkflow === "review" ? "Reviewing" : activeWorkflow === "teach" ? "Teaching" : "Capturing"}
        </div>
      )}

      {/* Orb */}
      <VoiceOrb state={orbState} className="py-6" />

      {/* Error display */}
      {error && (
        <div className="w-full rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive text-center">
          {error}
        </div>
      )}

      {/* Session summary */}
      {sessionSummary && (
        <div className="w-full rounded-lg border border-primary/30 bg-primary/5 p-4 text-sm">
          <p className="font-medium text-primary mb-1">Session Complete</p>
          <p className="text-muted-foreground">
            Duration: {Math.floor((sessionSummary.duration_seconds as number) || 0)}s
            {(sessionSummary.captures as number) > 0 && (
              <> &middot; Captures: {sessionSummary.captures as number}</>
            )}
            {(sessionSummary.reviews as number) > 0 && (
              <> &middot; Reviews: {sessionSummary.reviews as number}</>
            )}
            {(sessionSummary.teaches as number) > 0 && (
              <> &middot; Teaches: {sessionSummary.teaches as number}</>
            )}
            {sessionSummary.reviewed_count !== undefined && (
              <> &middot; {sessionSummary.review_correct as number}/{sessionSummary.reviewed_count as number} correct</>
            )}
          </p>
        </div>
      )}

      {/* Transcript */}
      {(isActive || transcript.length > 0) && (
        <VoiceTranscript entries={transcript} className="w-full" />
      )}

      {/* Progress */}
      {isActive && (
        <VoiceProgress
          duration={sessionDuration}
          lastFunctionResult={lastFunctionResult}
          className="w-full"
        />
      )}

      {/* Voice review queue */}
      {isActive && reviewActive && reviewQueue.length > 0 && (
        <VoiceReviewQueue
          items={reviewQueue}
          currentNumber={reviewCurrent}
          totalQuestions={reviewTotal}
          className="w-full md:fixed md:right-4 md:top-1/2 md:-translate-y-1/2 md:w-64 md:max-w-xs md:z-10"
        />
      )}

      {/* Connect / Disconnect button */}
      <div className="flex gap-3">
        {!isActive && !isConnecting ? (
          <Button size="lg" onClick={handleStart}>
            Start Conversation
          </Button>
        ) : (
          <Button
            size="lg"
            variant="destructive"
            onClick={handleEnd}
            disabled={isConnecting}
          >
            {isConnecting ? "Connecting..." : "End Session"}
          </Button>
        )}
      </div>
    </div>
  );
}
