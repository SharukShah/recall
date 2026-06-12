"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ReviewQuestion } from "@/types/api";

interface UpcomingQuestionsProps {
  questions: ReviewQuestion[];
  currentIndex: number;
}

export function UpcomingQuestions({ questions, currentIndex }: UpcomingQuestionsProps) {
  const [expanded, setExpanded] = useState(true);

  const upcoming = questions.slice(currentIndex + 1, currentIndex + 6);

  if (upcoming.length === 0) return null;

  return (
    <div className="rounded-lg border border-border bg-muted/30 dark:bg-muted/10">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
      >
        <span>Next up ({upcoming.length})</span>
        {expanded ? (
          <ChevronUp className="h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" />
        )}
      </button>
      <div
        className={`grid transition-all duration-200 ease-in-out ${
          expanded ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="overflow-hidden">
          <div className="space-y-1 px-3 pb-2">
            {upcoming.map((q, i) => (
              <div
                key={q.question_id}
                className="flex items-start gap-2 rounded-md px-2 py-1.5 text-xs text-muted-foreground"
              >
                <span className="shrink-0 font-mono text-[10px] mt-0.5 opacity-60">
                  {currentIndex + 2 + i}
                </span>
                <span className="line-clamp-1 flex-1">
                  {q.question_text.length > 60
                    ? q.question_text.slice(0, 60) + "…"
                    : q.question_text}
                </span>
                <Badge
                  variant="outline"
                  className="shrink-0 text-[10px] px-1.5 py-0 h-4 uppercase opacity-60"
                >
                  {q.question_type === "explain_back" ? "explain" : q.question_type}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
