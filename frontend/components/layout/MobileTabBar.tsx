"use client";

import { LayoutDashboard, PlusCircle, Brain, Clock, Search } from "lucide-react";
import { NavLink } from "./NavLink";

interface MobileTabBarProps {
  dueCount: number;
}

export function MobileTabBar({ dueCount }: MobileTabBarProps) {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t border-border bg-background h-16 md:hidden"
      role="navigation"
      aria-label="Main navigation"
    >
      <NavLink href="/" icon={LayoutDashboard} label="Dashboard" orientation="horizontal" />
      <NavLink href="/capture" icon={PlusCircle} label="Capture" orientation="horizontal" />
      <NavLink href="/search" icon={Search} label="Search" orientation="horizontal" />
      <NavLink href="/review" icon={Brain} label="Review" badge={dueCount} orientation="horizontal" />
      <NavLink href="/history" icon={Clock} label="History" orientation="horizontal" />
    </nav>
  );
}
