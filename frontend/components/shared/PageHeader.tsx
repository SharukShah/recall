"use client";

import { useEffect, useRef } from "react";

interface PageHeaderProps {
  title: string;
}

export function PageHeader({ title }: PageHeaderProps) {
  const ref = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    ref.current?.focus();
  }, []);

  return (
    <h1 ref={ref} tabIndex={-1} className="text-2xl font-semibold outline-none">{title}</h1>
  );
}
