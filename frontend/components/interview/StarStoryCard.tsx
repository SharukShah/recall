"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StarBreakdown } from "./StarBreakdown";
import { getStory, deleteStory } from "@/lib/api";
import type { StarStoryListItem, StarStory } from "@/types/api";
import { Star, ChevronDown, ChevronUp, Trash2, Loader2 } from "lucide-react";

interface StarStoryCardProps {
  item: StarStoryListItem;
  onDeleted?: () => void;
}

export function StarStoryCard({ item, onDeleted }: StarStoryCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [fullStory, setFullStory] = useState<StarStory | null>(null);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleToggle = async () => {
    if (expanded) {
      setExpanded(false);
      return;
    }

    if (!fullStory) {
      setLoading(true);
      try {
        const data = await getStory(item.id);
        setFullStory(data);
      } catch {
        // Silently fail, user can retry
      } finally {
        setLoading(false);
      }
    }
    setExpanded(true);
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteStory(item.id);
      onDeleted?.();
    } catch {
      setDeleting(false);
    }
  };

  return (
    <Card>
      <CardContent className="pt-4">
        <button
          onClick={handleToggle}
          className="w-full text-left"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 space-y-1">
              <p className="text-sm font-medium">{item.title}</p>
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="secondary" className="text-xs capitalize">
                  {item.competency.replace(/_/g, " ")}
                </Badge>
                <div className="flex items-center gap-0.5">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star
                      key={i}
                      className={`h-3 w-3 ${
                        i < item.strength_rating
                          ? "fill-yellow-400 text-yellow-400"
                          : "text-muted-foreground/30"
                      }`}
                    />
                  ))}
                </div>
                <span className="text-xs text-muted-foreground">
                  Practiced {item.times_practiced}x
                </span>
              </div>
            </div>
            <div className="shrink-0 pt-1">
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : expanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </div>
          </div>
        </button>

        {expanded && fullStory && (
          <div className="mt-4 space-y-3">
            <StarBreakdown story={fullStory} />
            <div className="flex justify-end">
              <Button
                size="sm"
                variant="ghost"
                onClick={handleDelete}
                disabled={deleting}
                className="text-destructive hover:text-destructive gap-1"
              >
                {deleting ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Trash2 className="h-3 w-3" />
                )}
                Delete
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
