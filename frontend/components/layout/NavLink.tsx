"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface NavLinkProps {
  href: string;
  icon: LucideIcon;
  label: string;
  badge?: number;
  orientation?: "horizontal" | "vertical";
}

export function NavLink({ href, icon: Icon, label, badge, orientation = "vertical" }: NavLinkProps) {
  const pathname = usePathname();
  const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href);

  if (orientation === "horizontal") {
    return (
      <Link
        href={href}
        className={cn(
          "flex flex-col items-center gap-1 px-3 py-2 text-xs transition-colors relative",
          isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
        )}
        aria-current={isActive ? "page" : undefined}
      >
        <Icon className="h-5 w-5" />
        <span>{label}</span>
        {badge !== undefined && badge > 0 && (
          <span
            className="absolute -top-0.5 right-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground"
            aria-label={`${badge} reviews due`}
          >
            {badge > 99 ? "99+" : badge}
          </span>
        )}
      </Link>
    );
  }

  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors relative",
        isActive
          ? "bg-primary/10 text-primary border-l-2 border-primary"
          : "text-muted-foreground hover:bg-accent hover:text-foreground"
      )}
      aria-current={isActive ? "page" : undefined}
    >
      <Icon className="h-5 w-5 shrink-0" />
      <span>{label}</span>
      {badge !== undefined && badge > 0 && (
        <span
          className="ml-auto flex h-5 min-w-[20px] items-center justify-center rounded-full bg-destructive px-1.5 text-[11px] font-bold text-destructive-foreground"
          aria-label={`${badge} reviews due`}
        >
          {badge > 99 ? "99+" : badge}
        </span>
      )}
    </Link>
  );
}
