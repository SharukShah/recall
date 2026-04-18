"use client";

import { useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface RatingButtonsProps {
  suggestedRating?: number;
  onRate: (rating: 1 | 2 | 3 | 4) => void;
  disabled: boolean;
}

const ratings = [
  { value: 1 as const, label: "Again", sublabel: "forgot", colorClass: "bg-rating-again hover:bg-red-600" },
  { value: 2 as const, label: "Hard", sublabel: "tough", colorClass: "bg-rating-hard hover:bg-orange-600" },
  { value: 3 as const, label: "Good", sublabel: "got it", colorClass: "bg-rating-good hover:bg-green-600" },
  { value: 4 as const, label: "Easy", sublabel: "obvious", colorClass: "bg-rating-easy hover:bg-blue-600" },
];

export function RatingButtons({ suggestedRating, onRate, disabled }: RatingButtonsProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (disabled) return;
      const key = parseInt(e.key);
      if (key >= 1 && key <= 4) {
        e.preventDefault();
        onRate(key as 1 | 2 | 3 | 4);
      }
    },
    [disabled, onRate]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium">How difficult was this?</p>
      <div
        className="grid grid-cols-2 sm:grid-cols-4 gap-2"
        role="group"
        aria-label="Rate your recall difficulty"
      >
        {ratings.map((r) => (
          <Button
            key={r.value}
            onClick={() => onRate(r.value)}
            disabled={disabled}
            className={cn(
              "flex flex-col items-center gap-0.5 h-auto py-3 text-white border-2 border-transparent",
              r.colorClass,
              suggestedRating === r.value && "ring-2 ring-white ring-offset-2 ring-offset-background"
            )}
            aria-label={`${r.label} — ${r.sublabel}`}
          >
            <span className="text-sm font-semibold">{r.label}</span>
            <span className="text-xs opacity-80">{r.sublabel}</span>
          </Button>
        ))}
      </div>
      <p className="text-xs text-muted-foreground hidden sm:block">
        Keyboard: press 1-4 to rate
      </p>
    </div>
  );
}
