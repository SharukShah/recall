"use client";

import { useCallback } from "react";
import { useVoiceAgent } from "@/hooks/useVoiceAgent";
import { VoiceOrb } from "@/components/voice/VoiceOrb";
import { VoiceTranscript } from "@/components/voice/VoiceTranscript";
import { VoiceProgress } from "@/components/voice/VoiceProgress";
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
