"use client";

import { cn } from "@/lib/utils";

type VoiceMode = "capture" | "review" | "teach";

interface ModeSelectorProps {
  selected: VoiceMode;
  onChange: (mode: VoiceMode) => void;
  disabled?: boolean;
  className?: string;
}

const MODES: { value: VoiceMode; label: string; description: string }[] = [
  { value: "capture", label: "Capture", description: "Dictate knowledge" },
  { value: "review", label: "Review", description: "Spaced repetition" },
  { value: "teach", label: "Teach", description: "Learn a topic" },
];

export function ModeSelector({
  selected,
  onChange,
  disabled,
  className,
}: ModeSelectorProps) {
  return (
    <div
      className={cn(
        "inline-flex rounded-lg border border-border bg-muted p-1 gap-1",
        className,
      )}
      role="tablist"
    >
      {MODES.map((m) => (
        <button
          key={m.value}
          role="tab"
          aria-selected={selected === m.value}
          disabled={disabled}
          onClick={() => onChange(m.value)}
          className={cn(
            "rounded-md px-4 py-2 text-sm font-medium transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            selected === m.value
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
            disabled && "opacity-50 cursor-not-allowed",
          )}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
