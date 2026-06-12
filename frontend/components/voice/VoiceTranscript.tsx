"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { TranscriptEntry } from "@/hooks/useVoiceAgent";

interface VoiceTranscriptProps {
  entries: TranscriptEntry[];
  className?: string;
}

export function VoiceTranscript({ entries, className }: VoiceTranscriptProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries]);

  if (entries.length === 0) {
    return (
      <div
        className={cn(
          "rounded-lg border border-border bg-card p-4 text-center text-sm text-muted-foreground",
          className,
        )}
      >
        Conversation will appear here...
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      className={cn(
        "rounded-lg border border-border bg-card overflow-y-auto max-h-[60vh] p-4 space-y-3",
        className,
      )}
    >
      {entries.map((entry, i) => {
        const isAgent = entry.role === "agent" || entry.role === "assistant";
        return (
          <div key={i} className={cn("flex gap-2 text-sm rounded-lg px-3 py-2", isAgent ? "bg-primary/5" : "bg-muted/50")}>
            <span
              className={cn(
                "font-semibold shrink-0",
                isAgent ? "text-primary" : "text-foreground",
              )}
            >
              {isAgent ? "ReCall:" : "You:"}
            </span>
            <span className="text-foreground/90">{entry.text}</span>
          </div>
        );
      })}
    </div>
  );
}
