import { Button } from "@/components/ui/button";

interface SessionHeaderProps {
  currentIndex: number;
  total: number;
  onEndSession: () => void;
}

export function SessionHeader({ currentIndex, total, onEndSession }: SessionHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <h1 className="text-2xl font-semibold">Review</h1>
      <div className="flex items-center gap-4">
        <span className="text-sm text-muted-foreground">
          {currentIndex + 1} / {total}
        </span>
        <Button variant="outline" size="sm" onClick={onEndSession}>
          End Session
        </Button>
      </div>
    </div>
  );
}
