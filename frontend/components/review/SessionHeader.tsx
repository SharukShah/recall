import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

interface SessionHeaderProps {
  currentIndex: number;
  total: number;
  onEndSession: () => void;
}

export function SessionHeader({ currentIndex, total, onEndSession }: SessionHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-xl font-bold">Review Session</h1>
        <p className="text-xs text-muted-foreground">
          Question {currentIndex + 1} of {total}
        </p>
      </div>
      <Button variant="ghost" size="sm" onClick={onEndSession} className="gap-1.5 text-muted-foreground hover:text-destructive">
        <X className="h-4 w-4" />
        End
      </Button>
    </div>
  );
}
