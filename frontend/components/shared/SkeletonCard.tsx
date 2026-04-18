import { cn } from "@/lib/utils";

interface SkeletonCardProps {
  lines?: number;
  className?: string;
}

export function SkeletonCard({ lines = 3, className }: SkeletonCardProps) {
  return (
    <div
      className={cn("rounded-lg border border-border p-4 md:p-6", className)}
      aria-hidden="true"
    >
      <div className="space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "h-4 animate-pulse rounded bg-muted",
              i === lines - 1 ? "w-2/3" : "w-full"
            )}
          />
        ))}
      </div>
    </div>
  );
}
