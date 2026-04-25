import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { EvaluateResponse } from "@/types/api";

interface FeedbackCardProps {
  evaluation: EvaluateResponse;
}

const scoreConfig = {
  correct: {
    label: "Correct",
    className: "text-green-700 bg-green-100 dark:bg-green-950 dark:text-green-400 border border-green-200 dark:border-green-800",
    icon: "✅",
  },
  partial: {
    label: "Partial",
    className: "text-yellow-700 bg-yellow-100 dark:bg-yellow-950 dark:text-yellow-400 border border-yellow-200 dark:border-yellow-800",
    icon: "🟡",
  },
  wrong: {
    label: "Incorrect",
    className: "text-red-700 bg-red-100 dark:bg-red-950 dark:text-red-400 border border-red-200 dark:border-red-800",
    icon: "❌",
  },
} as const;

export function FeedbackCard({ evaluation }: FeedbackCardProps) {
  const config = scoreConfig[evaluation.score as keyof typeof scoreConfig];
  
  // Safety check in case score is unexpected
  if (!config) {
    console.error("Unexpected score value:", evaluation.score);
    return null;
  }

  return (
    <Card>
      <CardContent className="pt-6 space-y-4">
        <div
          className={cn("inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold", config.className)}
          role="status"
          aria-label={`Your answer was ${config.label.toLowerCase()}`}
        >
          <span>{config.icon}</span>
          <span>{config.label}</span>
        </div>

        <div className="space-y-2 rounded-lg bg-secondary/50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Correct Answer</p>
          <p className="text-sm leading-relaxed">{evaluation.correct_answer}</p>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Feedback</p>
          <p className="text-sm leading-relaxed">{evaluation.feedback}</p>
        </div>
      </CardContent>
    </Card>
  );
}
