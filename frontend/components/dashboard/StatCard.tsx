import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  value: number | string;
  label: string;
  icon?: LucideIcon;
  className?: string;
  trend?: string;
}

export function StatCard({ value, label, icon: Icon, className, trend }: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card p-4 md:p-5 shadow-sm",
        className
      )}
      role="status"
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
          <p className="text-2xl font-bold md:text-3xl">{value}</p>
          {trend && <p className="text-xs text-muted-foreground">{trend}</p>}
        </div>
        {Icon && (
          <div className="rounded-lg bg-primary/10 p-2">
            <Icon className="h-4 w-4 text-primary" />
          </div>
        )}
      </div>
    </div>
  );
}
