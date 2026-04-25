import { Progress } from "@/components/ui/progress";

interface ProgressBarProps {
  current: number;
  total: number;
}

export function ReviewProgressBar({ current, total }: ProgressBarProps) {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <div className="space-y-1.5">
      <Progress
        value={percentage}
        role="progressbar"
        aria-valuenow={current}
        aria-valuemin={0}
        aria-valuemax={total}
        className="h-2"
      />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{current} answered</span>
        <span>{total - current} remaining</span>
      </div>
    </div>
  );
}
