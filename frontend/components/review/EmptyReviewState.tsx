import Link from "next/link";
import { BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EmptyReviewState() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      <BookOpen className="h-12 w-12 text-muted-foreground" />
      <p className="text-lg font-medium">All caught up!</p>
      <p className="text-sm text-muted-foreground max-w-sm">
        Nothing to review right now. Capture something new to generate review questions.
      </p>
      <Button asChild>
        <Link href="/capture">Capture Knowledge</Link>
      </Button>
    </div>
  );
}
