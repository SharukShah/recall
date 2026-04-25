"use client";

import { cn } from "@/lib/utils";
import type { FunctionResult } from "@/hooks/useVoiceAgent";

interface VoiceProgressProps {
  duration: number;
  lastFunctionResult: FunctionResult | null;
  className?: string;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function VoiceProgress({
  duration,
  lastFunctionResult,
  className,
}: VoiceProgressProps) {
  // Extract progress from function results — infer workflow from function name
  let progressText = "";
  let progressValue = 0;
  let progressMax = 0;

  if (lastFunctionResult) {
    const r = lastFunctionResult.result;
    const fn = lastFunctionResult.name;

    if (fn === "start_review_session") {
      const due = (r.due_count as number) || 0;
      if (due > 0) {
        progressText = `${due} questions to review`;
        progressMax = due;
        progressValue = 0;
      } else {
        progressText = r.message as string || "No reviews due";
      }
    } else if (fn === "get_next_question") {
      const qNum = (r.question_number as number) || 0;
      const total = (r.total_questions as number) || 0;
      if (total > 0) {
        progressText = `Question ${qNum} of ${total}`;
        progressValue = qNum;
        progressMax = total;
      }
      if (r.done) {
        progressText = `All ${r.reviewed_count || 0} reviewed — ${r.correct_count || 0} correct!`;
        progressValue = progressMax;
      }
    } else if (fn === "get_current_teach_chunk" || fn === "submit_teach_answer") {
      const idx = ((r.chunk_index as number) ?? 0) + 1;
      const total = (r.total_chunks as number) || 0;
      if (total > 0) {
        progressText = `Chunk ${idx} of ${total}`;
        progressValue = idx;
        progressMax = total;
      }
      if (r.is_complete) {
        progressText = "Teaching complete!";
        progressValue = progressMax;
      }
    } else if (fn === "finish_capture") {
      const facts = (r.facts_count as number) || 0;
      const questions = (r.questions_count as number) || 0;
      progressText = `Captured ${facts} facts, ${questions} questions`;
    } else if (fn === "rate_question") {
      const days = (r.interval_days as number) || 0;
      const label = (r.state_label as string) || "";
      if (days < 1) {
        progressText = `Next review in ${Math.max(1, Math.round(days * 24 * 60))} min`;
      } else if (days < 2) {
        progressText = "Next review tomorrow";
      } else {
        progressText = `Next review in ${Math.round(days)} days`;
      }
      if (label) progressText += ` · ${label}`;
    } else if (fn === "get_user_context") {
      const due = (r.due_count as number) || 0;
      const streak = (r.streak_days as number) || 0;
      progressText = `${due} due · ${streak} day streak`;
    }
  }

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-3 space-y-2",
        className,
      )}
    >
      <div className="flex items-center justify-between text-sm">
        {progressText ? (
          <span className="text-foreground font-medium">{progressText}</span>
        ) : (
          <span className="text-muted-foreground">Voice Session</span>
        )}
        <span className="text-muted-foreground font-mono text-xs">
          {formatDuration(duration)}
        </span>
      </div>
      {progressMax > 0 && (
        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-primary transition-all duration-300"
            style={{ width: `${(progressValue / progressMax) * 100}%` }}
          />
        </div>
      )}
    </div>
  );
}
