"use client";

import { LayoutDashboard, Plus, Brain, Clock, Search, GraduationCap, Sunset, Mic, Settings, Castle, Activity, Network } from "lucide-react";
import { NavLink } from "./NavLink";

interface DesktopSidebarProps {
  dueCount: number;
}

export function DesktopSidebar({ dueCount }: DesktopSidebarProps) {
  return (
    <aside
      className="hidden md:flex md:w-60 md:flex-col md:fixed md:inset-y-0 border-r border-border bg-background z-40"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="flex h-14 items-center px-6 border-b border-border">
        <span className="text-xl font-bold text-primary">ReCall</span>
      </div>
      <nav className="flex flex-col gap-0.5 p-3 flex-1 overflow-y-auto">
        <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Main</p>
        <NavLink href="/" icon={LayoutDashboard} label="Dashboard" />
        <NavLink href="/capture" icon={Plus} label="Capture" />
        <NavLink href="/review" icon={Brain} label="Review" badge={dueCount} />

        <p className="px-3 py-2 mt-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Learn</p>
        <NavLink href="/teach" icon={GraduationCap} label="Teach Me" />
        <NavLink href="/voice" icon={Mic} label="Voice Agent" />
        <NavLink href="/loci" icon={Castle} label="Memory Palace" />

        <p className="px-3 py-2 mt-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Explore</p>
        <NavLink href="/search" icon={Search} label="Search" />
        <NavLink href="/graph" icon={Network} label="Knowledge Graph" />
        <NavLink href="/analytics" icon={Activity} label="Analytics" />

        <p className="px-3 py-2 mt-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Other</p>
        <NavLink href="/reflect" icon={Sunset} label="Reflect" />
        <NavLink href="/history" icon={Clock} label="History" />
        <div className="mt-auto pt-3 border-t border-border">
          <NavLink href="/settings" icon={Settings} label="Settings" />
        </div>
      </nav>
    </aside>
  );
}
