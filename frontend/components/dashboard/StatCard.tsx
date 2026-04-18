import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  value: number | string;
  label: string;
  icon?: LucideIcon;
  className?: string;
}

export function StatCard({ value, label, icon: Icon, className }: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border p-4 md:p-6",
        className
      )}
      role="status"
    >
      <div className="flex items-center gap-3">
        {Icon && <Icon className="h-5 w-5 text-primary shrink-0" />}
        <div>
          <p className="text-3xl font-bold md:text-4xl">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </div>
    </div>
  );
}
