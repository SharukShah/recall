"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { StarBreakdown } from "@/components/interview/StarBreakdown";
import { captureBehavioral } from "@/lib/api";
import type { BehavioralCaptureResponse, StarStory } from "@/types/api";
import { Loader2, CheckCircle2 } from "lucide-react";
import Link from "next/link";

const COMPETENCIES = [
  "leadership",
  "teamwork",
  "problem_solving",
  "communication",
  "adaptability",
  "conflict_resolution",
  "initiative",
  "time_management",
];

export default function NewBehavioralStoryPage() {
  const [narrative, setNarrative] = useState("");
  const [competency, setCompetency] = useState("leadership");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BehavioralCaptureResponse | null>(null);

  const handleSubmit = async () => {
    if (!narrative.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const data = await captureBehavioral(narrative, competency);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to capture story");
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    const storyPreview: StarStory = {
      id: result.story_id,
      capture_id: result.capture_id,
      title: result.title,
      situation: result.situation,
      task: result.task,
      action: result.action,
      result: result.result,
      competency: result.competency,
      strength_rating: result.strength_rating,
      times_practiced: 0,
      last_practiced_at: null,
      created_at: new Date().toISOString(),
    };

    return (
      <div className="space-y-6 max-w-2xl mx-auto">
        <PageHeader title="Story Captured" />

        <div className="flex items-center gap-3 rounded-lg bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900 p-4">
          <CheckCircle2 className="h-5 w-5 text-green-600" />
          <div>
            <p className="text-sm font-medium">{result.title}</p>
            <p className="text-xs text-muted-foreground capitalize">
              {result.competency.replace(/_/g, " ")} • Strength: {result.strength_rating}/5
            </p>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Extracted STAR Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <StarBreakdown story={storyPreview} />
          </CardContent>
        </Card>

        <div className="flex gap-3">
          <Button
            onClick={() => {
              setResult(null);
              setNarrative("");
            }}
            className="flex-1"
          >
            Capture Another
          </Button>
          <Link href="/interview/behavioral" className="flex-1">
            <Button variant="outline" className="w-full">Back to Stories</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div className="flex items-center justify-between">
        <PageHeader title="Capture Story" />
        <Link href="/interview/behavioral">
          <Button variant="ghost" size="sm">← Back</Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tell Your Story</CardTitle>
          <p className="text-sm text-muted-foreground">
            Describe a work experience and we&apos;ll extract the STAR structure for you.
          </p>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Competency */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Competency</Label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {COMPETENCIES.map((c) => (
                <button
                  key={c}
                  onClick={() => setCompetency(c)}
                  className={`rounded-lg border px-3 py-2 text-xs font-medium capitalize transition-colors ${
                    competency === c
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border hover:border-primary/40 hover:bg-accent"
                  }`}
                >
                  {c.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          </div>

          {/* Narrative */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Your Experience</Label>
            <Textarea
              value={narrative}
              onChange={(e) => setNarrative(e.target.value)}
              placeholder="Tell us about a time when you demonstrated this competency. Include the situation, what you did, and the outcome..."
              rows={10}
              className="resize-none"
            />
            <p className="text-xs text-muted-foreground">
              {narrative.length} characters — aim for at least 200 for a good STAR breakdown
            </p>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button
            onClick={handleSubmit}
            disabled={submitting || narrative.trim().length < 50}
            className="w-full"
            size="lg"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Extracting STAR...
              </>
            ) : (
              "Capture & Extract"
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
