"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface VoiceReviewItem {
  question_id: string;
  question_text: string;
  question_type: string;
  question_number: number;
}

interface VoiceReviewQueueProps {
  items: VoiceReviewItem[];
  currentNumber: number;
  totalQuestions: number;
  className?: string;
}

export function VoiceReviewQueue({
  items,
  currentNumber,
  totalQuestions,
  className,
}: VoiceReviewQueueProps) {
  if (items.length === 0) return null;

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-3 space-y-2",
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">
          Review Queue
        </span>
        <span className="text-[10px] text-muted-foreground font-mono">
          {currentNumber}/{totalQuestions}
        </span>
      </div>
      <div className="space-y-1">
        {items.map((item) => {
          const isCurrent = item.question_number === currentNumber;
          return (
            <div
              key={item.question_id}
              className={cn(
                "flex items-start gap-2 rounded-md px-2 py-1.5 text-xs transition-colors",
                isCurrent
                  ? "bg-primary/10 text-foreground"
                  : "text-muted-foreground opacity-60",
              )}
            >
              <span
                className={cn(
                  "shrink-0 font-mono text-[10px] mt-0.5",
                  isCurrent && "font-bold text-primary",
                )}
              >
                {item.question_number}
              </span>
              <span className="line-clamp-1 flex-1">
                {item.question_text.length > 50
                  ? item.question_text.slice(0, 50) + "…"
                  : item.question_text}
              </span>
              <Badge
                variant={isCurrent ? "secondary" : "outline"}
                className="shrink-0 text-[10px] px-1.5 py-0 h-4 uppercase"
              >
                {item.question_type === "explain_back" ? "explain" : item.question_type}
              </Badge>
            </div>
          );
        })}
      </div>
    </div>
  );
}
