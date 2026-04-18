import { type RefObject } from "react";
import Link from "next/link";
import { PartyPopper } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDuration } from "@/lib/utils";

interface SessionSummaryProps {
  stats: {
    total: number;
    answered: number;
    ratings: Record<1 | 2 | 3 | 4, number>;
    startTime: number;
  };
  headingRef?: RefObject<HTMLHeadingElement>;
}

const ratingLabels = [
  { key: 1, label: "Again", color: "bg-rating-again" },
  { key: 2, label: "Hard", color: "bg-rating-hard" },
  { key: 3, label: "Good", color: "bg-rating-good" },
  { key: 4, label: "Easy", color: "bg-rating-easy" },
] as const;

export function SessionSummary({ stats, headingRef }: SessionSummaryProps) {
  const duration = Date.now() - stats.startTime;
  const accuracy =
    stats.answered > 0
      ? Math.round(((stats.ratings[3] + stats.ratings[4]) / stats.answered) * 100)
      : 0;
  const maxRating = Math.max(...Object.values(stats.ratings), 1);

  return (
    <div className="flex flex-col items-center gap-6 py-8 animate-crossfade-in">
      <PartyPopper className="h-12 w-12 text-primary" />
      <h2 ref={headingRef} tabIndex={-1} className="text-3xl font-bold outline-none">Session Complete!</h2>

      <Card className="w-full max-w-md">
        <CardContent className="pt-6 space-y-4">
          <div className="text-center space-y-1">
            <p className="text-lg font-semibold">
              {stats.answered} questions reviewed
            </p>
            <p className="text-sm text-muted-foreground">
              in {formatDuration(duration)}
            </p>
          </div>

          <div className="space-y-2">
            {ratingLabels.map(({ key, label, color }) => (
              <div key={key} className="flex items-center gap-3">
                <span className="text-sm w-12 text-right">{label}:</span>
                <span className="text-sm w-6 font-medium">{stats.ratings[key]}</span>
                <div className="flex-1 h-4 rounded bg-muted overflow-hidden">
                  <div
                    className={`h-full rounded ${color} transition-all`}
                    style={{
                      width: `${(stats.ratings[key] / maxRating) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          <p className="text-center text-sm text-muted-foreground">
            Accuracy: {accuracy}% (Good + Easy)
          </p>
        </CardContent>
      </Card>

      <Button asChild size="lg">
        <Link href="/">Back to Dashboard</Link>
      </Button>
    </div>
  );
}
