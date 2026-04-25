"use client";

import { cn } from "@/lib/utils";

type OrbState = "idle" | "listening" | "speaking" | "thinking";

interface VoiceOrbProps {
  state: OrbState;
  className?: string;
}

export function VoiceOrb({ state, className }: VoiceOrbProps) {
  const label =
    state === "idle"
      ? "Ready"
      : state === "listening"
        ? "Listening..."
        : state === "speaking"
          ? "Speaking..."
          : "Thinking...";

  return (
    <div className={cn("flex flex-col items-center gap-3", className)}>
      <div className="relative flex items-center justify-center">
        {/* Outer pulse ring */}
        <div
          className={cn(
            "absolute rounded-full transition-all duration-500",
            state === "listening" &&
              "h-28 w-28 animate-ping bg-primary/20",
            state === "speaking" &&
              "h-28 w-28 animate-pulse bg-green-500/20",
            state === "thinking" &&
              "h-28 w-28 animate-pulse bg-yellow-500/20",
            state === "idle" && "h-24 w-24 bg-muted/30",
          )}
        />
        {/* Inner orb */}
        <div
          className={cn(
            "relative z-10 flex h-20 w-20 items-center justify-center rounded-full transition-all duration-300",
            state === "idle" && "bg-muted",
            state === "listening" &&
              "bg-primary shadow-lg shadow-primary/30 scale-110",
            state === "speaking" &&
              "bg-green-500 shadow-lg shadow-green-500/30 scale-105",
            state === "thinking" &&
              "bg-yellow-500 shadow-lg shadow-yellow-500/30",
          )}
        >
          {/* Mic / Speaker / Thinking icon */}
          {state === "listening" && (
            <svg className="h-8 w-8 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
            </svg>
          )}
          {state === "speaking" && (
            <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
            </svg>
          )}
          {state === "thinking" && (
            <svg className="h-8 w-8 text-white animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
            </svg>
          )}
          {state === "idle" && (
            <svg className="h-8 w-8 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
            </svg>
          )}
        </div>
      </div>
      <span
        className={cn(
          "text-sm font-medium",
          state === "idle" && "text-muted-foreground",
          state === "listening" && "text-primary",
          state === "speaking" && "text-green-600 dark:text-green-400",
          state === "thinking" && "text-yellow-600 dark:text-yellow-400",
        )}
      >
        {label}
      </span>
    </div>
  );
}
