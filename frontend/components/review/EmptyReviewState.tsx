import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EmptyReviewState() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      <div className="rounded-full bg-green-100 dark:bg-green-900/30 p-4">
        <CheckCircle2 className="h-10 w-10 text-green-500" />
      </div>
      <p className="text-xl font-bold">All caught up! 🎉</p>
      <p className="text-sm text-muted-foreground max-w-sm">
        No reviews due right now. Capture new knowledge to generate more review questions.
      </p>
      <div className="flex gap-3">
        <Button asChild>
          <Link href="/capture">Capture Knowledge</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/">Back to Dashboard</Link>
        </Button>
      </div>
    </div>
  );
}
