import Link from "next/link";
import { truncateText, formatRelativeDate } from "@/lib/utils";
import type { CaptureListItem } from "@/types/api";

interface CaptureCardProps {
  capture: CaptureListItem;
}

export function CaptureCard({ capture }: CaptureCardProps) {
  return (
    <Link
      href={`/history/${capture.id}`}
      className="block rounded-lg border border-border p-4 md:p-5 hover:bg-accent transition-colors"
    >
      <p className="text-sm font-medium leading-relaxed">
        {truncateText(capture.raw_text, 150)}
      </p>
      <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
        <span>{capture.facts_count} facts</span>
        <span>·</span>
        <span>{formatRelativeDate(capture.created_at)}</span>
      </div>
    </Link>
  );
}
