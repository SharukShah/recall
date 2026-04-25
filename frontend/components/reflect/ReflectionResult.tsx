"use client";

import { CheckCircle2, Brain, Flame, RotateCcw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ReflectionResponse } from "@/types/api";

interface ReflectionResultProps {
  result: ReflectionResponse;
  onReflectAgain: () => void;
}

export function ReflectionResult({ result, onReflectAgain }: ReflectionResultProps) {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-6 space-y-4 text-center">
          <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto" />
          <h2 className="text-lg font-semibold">Reflection Saved!</h2>

          {result.message ? (
            <p className="text-sm text-muted-foreground">{result.message}</p>
          ) : (
            <div className="flex justify-center gap-4 text-sm">
              <div className="flex items-center gap-1.5">
                <Brain className="h-4 w-4 text-primary" />
                <span>{result.facts_count} facts extracted</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span>{result.questions_count} questions created</span>
              </div>
            </div>
          )}

          <div className="flex justify-center">
            <Badge variant="secondary" className="text-sm">
              <Flame className="h-3.5 w-3.5 mr-1" />
              {result.streak_days} day streak
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Button onClick={onReflectAgain} variant="outline" className="w-full">
        <RotateCcw className="mr-2 h-4 w-4" />
        Reflect Again
      </Button>
    </div>
  );
}
