import { Badge } from "@/components/ui/badge";
import type { Fact } from "@/types/api";

interface FactItemProps {
  fact: Fact;
}

export function FactItem({ fact }: FactItemProps) {
  return (
    <li className="flex items-start gap-2 py-2">
      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
      <div className="space-y-1">
        <p className="text-sm">{fact.content}</p>
        <Badge variant="secondary" className="text-xs">
          {fact.content_type}
        </Badge>
      </div>
    </li>
  );
}
