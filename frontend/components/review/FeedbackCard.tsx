import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { EvaluateResponse } from "@/types/api";

interface FeedbackCardProps {
  evaluation: EvaluateResponse;
}

const scoreConfig = {
  correct: {
    label: "Correct",
    className: "text-green-600 bg-green-50 dark:bg-green-950 dark:text-green-400",
    icon: "✓",
  },
  partial: {
    label: "Partial",
    className: "text-yellow-600 bg-yellow-50 dark:bg-yellow-950 dark:text-yellow-400",
    icon: "~",
  },
  incorrect: {
    label: "Incorrect",
    className: "text-red-600 bg-red-50 dark:bg-red-950 dark:text-red-400",
    icon: "✗",
  },
};

export function FeedbackCard({ evaluation }: FeedbackCardProps) {
  const config = scoreConfig[evaluation.score];

  return (
    <Card>
      <CardContent className="pt-6 space-y-4">
        <div
          className={cn("inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-semibold", config.className)}
          role="status"
          aria-label={`Your answer was ${config.label.toLowerCase()}`}
        >
          <span>{config.icon}</span>
          <span>{config.label}</span>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">Correct Answer:</p>
          <p className="text-sm leading-relaxed">{evaluation.correct_answer}</p>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">Feedback:</p>
          <p className="text-sm leading-relaxed">{evaluation.feedback}</p>
        </div>
      </CardContent>
    </Card>
  );
}
