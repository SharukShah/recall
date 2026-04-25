"use client";

import { Sunset, Flame, CheckCircle2 } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { ReflectionForm } from "@/components/reflect/ReflectionForm";
import { ReflectionResult } from "@/components/reflect/ReflectionResult";
import { useReflection } from "@/hooks/useReflection";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

export default function ReflectPage() {
  const reflection = useReflection();

  // Already reflected today
  if (reflection.status?.completed_today && !reflection.result) {
    return (
      <div className="space-y-6">
        <PageHeader title="Reflect" />
        <Card>
          <CardContent className="pt-6 space-y-4 text-center">
            <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto" />
            <h2 className="text-lg font-semibold">Already reflected today!</h2>
            <p className="text-sm text-muted-foreground">
              Come back tomorrow for your next reflection.
            </p>
            <Badge variant="secondary" className="text-sm">
              <Flame className="h-3.5 w-3.5 mr-1" />
              {reflection.status.streak_days} day streak
            </Badge>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show result after submission
  if (reflection.result) {
    return (
      <div className="space-y-6">
        <PageHeader title="Reflect" />
        <ReflectionResult result={reflection.result} onReflectAgain={reflection.reset} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Reflect" />
      <div className="text-center space-y-2">
        <Sunset className="h-12 w-12 text-primary mx-auto" />
        <p className="text-sm text-muted-foreground">
          Take a moment to reflect on what you learned today. Even 1-2 sentences help.
        </p>
        {reflection.status && reflection.status.streak_days > 0 && (
          <Badge variant="secondary" className="text-sm">
            <Flame className="h-3.5 w-3.5 mr-1" />
            {reflection.status.streak_days} day streak
          </Badge>
        )}
      </div>
      <ReflectionForm onSubmit={reflection.submit} isSubmitting={reflection.submitting} />
      {reflection.error && (
        <p className="text-sm text-destructive text-center">{reflection.error}</p>
      )}
    </div>
  );
}
