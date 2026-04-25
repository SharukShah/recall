import Link from "next/link";
import { truncateText, formatRelativeDate } from "@/lib/utils";
import { ChevronRight, FileText, Mic, Link as LinkIcon } from "lucide-react";
import type { CaptureListItem } from "@/types/api";

interface CaptureCardProps {
  capture: CaptureListItem;
}

const sourceConfig: Record<string, { label: string; icon: typeof FileText }> = {
  text: { label: "Text", icon: FileText },
  voice: { label: "Voice", icon: Mic },
  url: { label: "URL", icon: LinkIcon },
};

export function CaptureCard({ capture }: CaptureCardProps) {
  const source = sourceConfig[capture.source_type] || sourceConfig.text;
  const SourceIcon = source.icon;

  return (
    <Link
      href={`/history/${capture.id}`}
      className="group flex items-center gap-3 rounded-xl border border-border bg-card p-4 hover:border-primary/30 hover:shadow-sm transition-all"
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-relaxed line-clamp-2">
          {truncateText(capture.raw_text, 150)}
        </p>
        <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5">
            <SourceIcon className="h-3 w-3" />
            {source.label}
          </span>
          <span>{capture.facts_count} facts</span>
          <span>·</span>
          <span>{formatRelativeDate(capture.created_at)}</span>
        </div>
      </div>
      <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 group-hover:text-primary transition-colors" />
    </Link>
  );
}
