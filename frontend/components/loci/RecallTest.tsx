"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle2, XCircle, Info } from "lucide-react";
import type { LociRecallResponse } from "@/types/loci";

interface RecallTestProps {
  totalItems: number;
  onSubmit: (items: string[]) => void;
  result?: LociRecallResponse;
  disabled?: boolean;
}

export function RecallTest({ totalItems, onSubmit, result, disabled }: RecallTestProps) {
  const [recalledItems, setRecalledItems] = useState<string[]>(
    Array(totalItems).fill("")
  );

  const updateRecalledItem = (index: number, value: string) => {
    const updated = [...recalledItems];
    updated[index] = value;
    setRecalledItems(updated);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(recalledItems.filter((item) => item.trim() !== ""));
  };

  if (result) {
    const percentage = Math.round((result.score / result.total) * 100);
    return (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Recall Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-center space-y-2">
              <div className="text-5xl font-bold text-primary">{percentage}%</div>
              <div className="text-muted-foreground">
                {result.score} out of {result.total} correct
              </div>
            </div>

            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>{result.feedback}</AlertDescription>
            </Alert>

            <div className="space-y-2">
              <Label>Details</Label>
              {result.details.map((detail) => (
                <div
                  key={detail.position}
                  className={`p-3 rounded-lg border ${
                    detail.correct
                      ? "bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800"
                      : "bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800"
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {detail.correct ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5" />
                    )}
                    <div className="flex-1 space-y-1">
                      <div className="font-semibold text-sm">
                        Position {detail.position}: {detail.location_hint}
                      </div>
                      <div className="text-sm">
                        <span className="text-muted-foreground">Expected: </span>
                        <span className="font-medium">{detail.expected}</span>
                      </div>
                      {!detail.correct && (
                        <div className="text-sm">
                          <span className="text-muted-foreground">You recalled: </span>
                          <span className="font-medium">
                            {detail.recalled || "(nothing)"}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-4">
              <Button
                variant="outline"
                onClick={() => window.location.reload()}
                className="w-full"
              >
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Test Your Recall</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              Walk through your memory palace mentally and recall the items in order.
              Leave blank if you can't remember.
            </AlertDescription>
          </Alert>

          <div className="space-y-3">
            {recalledItems.map((item, index) => (
              <div key={index} className="space-y-1">
                <Label htmlFor={`item-${index}`}>
                  Item {index + 1}
                </Label>
                <Input
                  id={`item-${index}`}
                  value={item}
                  onChange={(e) => updateRecalledItem(index, e.target.value)}
                  placeholder={`What was at position ${index + 1}?`}
                  disabled={disabled}
                />
              </div>
            ))}
          </div>

          <Button type="submit" disabled={disabled} className="w-full">
            Submit Recall
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
