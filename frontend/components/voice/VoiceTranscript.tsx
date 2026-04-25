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
        "rounded-lg border border-border bg-card overflow-y-auto max-h-64 p-3 space-y-2",
        className,
      )}
    >
      {entries.map((entry, i) => (
        <div key={i} className="flex gap-2 text-sm">
          <span
            className={cn(
              "font-semibold shrink-0",
              entry.role === "agent"
                ? "text-primary"
                : "text-foreground",
            )}
          >
            {entry.role === "agent" ? "Agent:" : "You:"}
          </span>
          <span className="text-foreground/90">{entry.text}</span>
        </div>
      ))}
    </div>
  );
}
