"use client";

import { LayoutDashboard, Plus, Brain, Clock, Search } from "lucide-react";
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
      <nav className="flex flex-col gap-1 p-3 flex-1">
        <NavLink href="/" icon={LayoutDashboard} label="Dashboard" />
        <NavLink href="/capture" icon={Plus} label="Capture" />
        <NavLink href="/search" icon={Search} label="Search" />
        <NavLink href="/review" icon={Brain} label="Review" badge={dueCount} />
        <NavLink href="/history" icon={Clock} label="History" />
      </nav>
    </aside>
  );
}
