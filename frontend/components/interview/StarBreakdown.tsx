"use client";

import type { StarStory } from "@/types/api";

interface StarBreakdownProps {
  story: StarStory;
}

const sections = [
  { key: "situation" as const, label: "Situation", color: "border-blue-500 bg-blue-50 dark:bg-blue-950/20" },
  { key: "task" as const, label: "Task", color: "border-green-500 bg-green-50 dark:bg-green-950/20" },
  { key: "action" as const, label: "Action", color: "border-orange-500 bg-orange-50 dark:bg-orange-950/20" },
  { key: "result" as const, label: "Result", color: "border-purple-500 bg-purple-50 dark:bg-purple-950/20" },
];

export function StarBreakdown({ story }: StarBreakdownProps) {
  return (
    <div className="space-y-3">
      {sections.map((s) => (
        <div key={s.key} className={`rounded-lg border-l-4 ${s.color} p-3`}>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            {s.label}
          </p>
          <p className="text-sm leading-relaxed">{story[s.key]}</p>
        </div>
      ))}
    </div>
  );
}
