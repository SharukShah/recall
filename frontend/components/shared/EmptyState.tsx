import Link from "next/link";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  message: string;
  subMessage?: string;
  cta?: {
    label: string;
    href: string;
  };
}

export function EmptyState({ message, subMessage, cta }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      <p className="text-lg font-medium text-foreground">{message}</p>
      {subMessage && (
        <p className="text-sm text-muted-foreground max-w-sm">{subMessage}</p>
      )}
      {cta && (
        <Button asChild>
          <Link href={cta.href}>{cta.label}</Link>
        </Button>
      )}
    </div>
  );
}
