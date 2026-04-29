"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { WeakCategoriesResponse } from "@/types/api";
import { AlertTriangle } from "lucide-react";
import Link from "next/link";

interface WeakAreasCardProps {
  data: WeakCategoriesResponse;
}

export function WeakAreasCard({ data }: WeakAreasCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          Weak Areas
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Categories needing the most attention
        </p>
      </CardHeader>
      <CardContent>
        {data.weak_categories.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No weak areas — great job!
          </p>
        ) : (
          <div className="space-y-4">
            {data.weak_categories.map((wc) => {
              const retentionPct = Math.round(wc.avg_retention * 100);
              const failPct = Math.round(wc.fail_rate * 100);

              return (
                <div key={wc.category} className="space-y-2">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium capitalize">
                        {wc.category.replace("_", " ")}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {wc.total_questions} questions • {failPct}% fail rate
                      </p>
                      <p className="text-xs text-blue-600 mt-0.5">{wc.suggested_action}</p>
                    </div>
                    <Link href={`/review?categories=${encodeURIComponent(wc.category)}`}>
                      <Button size="sm" variant="outline">
                        Practice
                      </Button>
                    </Link>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Retention</span>
                      <span className={retentionPct < 50 ? "text-red-500" : ""}>{retentionPct}%</span>
                    </div>
                    <Progress value={retentionPct} className="h-1.5" />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
