"use client";

import { Card } from "@/components/ui/card";
import type { BehavioralCoverageResponse } from "@/types/api";
import { Users, Star } from "lucide-react";

interface CompetencyCoverageGridProps {
  data: BehavioralCoverageResponse;
  selectedCompetency: string | null;
  onSelect: (competency: string | null) => void;
}

export function CompetencyCoverageGrid({
  data,
  selectedCompetency,
  onSelect,
}: CompetencyCoverageGridProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium flex items-center gap-2">
          <Users className="h-4 w-4" />
          Competency Coverage ({data.covered_competencies}/{data.total_competencies})
        </h3>
        {selectedCompetency && (
          <button
            onClick={() => onSelect(null)}
            className="text-xs text-primary hover:underline"
          >
            Clear filter
          </button>
        )}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {data.competencies.map((comp) => {
          const isSelected = selectedCompetency === comp.competency;
          const hasCoverage = comp.story_count > 0;

          return (
            <button
              key={comp.competency}
              onClick={() => onSelect(isSelected ? null : comp.competency)}
              className={`rounded-lg border p-3 text-left transition-colors ${
                isSelected
                  ? "border-primary bg-primary/10"
                  : hasCoverage
                    ? "border-green-200 bg-green-50 hover:bg-green-100 dark:border-green-900 dark:bg-green-950/30 dark:hover:bg-green-950/50"
                    : "border-border bg-muted/30 hover:bg-accent"
              }`}
            >
              <p className="text-xs font-medium capitalize truncate">
                {comp.competency.replace(/_/g, " ")}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {comp.story_count} {comp.story_count === 1 ? "story" : "stories"}
              </p>
              {comp.avg_strength !== null && comp.avg_strength > 0 && (
                <div className="flex items-center gap-0.5 mt-1">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star
                      key={i}
                      className={`h-2.5 w-2.5 ${
                        i < Math.round(comp.avg_strength!)
                          ? "fill-yellow-400 text-yellow-400"
                          : "text-muted-foreground/30"
                      }`}
                    />
                  ))}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
