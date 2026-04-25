"use client";

import { LayoutDashboard, PlusCircle, Brain, Clock, Mic, MoreHorizontal } from "lucide-react";
import { NavLink } from "./NavLink";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface MobileTabBarProps {
  dueCount: number;
}

export function MobileTabBar({ dueCount }: MobileTabBarProps) {
  const [showMore, setShowMore] = useState(false);
  const pathname = usePathname();

  const moreItems = [
    { href: "/teach", label: "Teach Me" },
    { href: "/voice", label: "Voice Agent" },
    { href: "/reflect", label: "Reflect" },
    { href: "/loci", label: "Memory Palace" },
    { href: "/graph", label: "Knowledge Graph" },
    { href: "/analytics", label: "Analytics" },
    { href: "/search", label: "Search" },
    { href: "/settings", label: "Settings" },
  ];

  const isMoreActive = moreItems.some(item => pathname.startsWith(item.href));

  return (
    <>
      {/* More menu overlay */}
      {showMore && (
        <div className="fixed inset-0 z-40 bg-black/40" onClick={() => setShowMore(false)}>
          <div
            className="absolute bottom-16 left-0 right-0 bg-background border-t border-border rounded-t-xl p-3 shadow-lg animate-slide-up"
            onClick={e => e.stopPropagation()}
          >
            <div className="grid grid-cols-4 gap-2">
              {moreItems.map(item => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setShowMore(false)}
                  className={cn(
                    "flex flex-col items-center gap-1 p-2.5 rounded-lg text-[11px] font-medium transition-colors",
                    pathname.startsWith(item.href)
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      <nav
        className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t border-border bg-background/95 backdrop-blur-sm h-16 md:hidden safe-bottom"
        role="navigation"
        aria-label="Main navigation"
      >
        <NavLink href="/" icon={LayoutDashboard} label="Home" orientation="horizontal" />
        <NavLink href="/capture" icon={PlusCircle} label="Capture" orientation="horizontal" />
        <NavLink href="/review" icon={Brain} label="Review" badge={dueCount} orientation="horizontal" />
        <NavLink href="/history" icon={Clock} label="History" orientation="horizontal" />
        <button
          onClick={() => setShowMore(!showMore)}
          className={cn(
            "flex flex-col items-center gap-1 px-3 py-2 text-xs transition-colors",
            isMoreActive || showMore ? "text-primary" : "text-muted-foreground hover:text-foreground"
          )}
          aria-label="More options"
        >
          <MoreHorizontal className="h-5 w-5" />
          <span>More</span>
        </button>
      </nav>
    </>
  );
}
