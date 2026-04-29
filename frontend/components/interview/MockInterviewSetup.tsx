"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { startInterview } from "@/lib/api";
import type { StartInterviewResponse } from "@/types/api";
import { Brain, Loader2 } from "lucide-react";
import Link from "next/link";

const TOPICS = [
  { value: "python", label: "Python" },
  { value: "dsa", label: "Data Structures & Algorithms" },
  { value: "system_design", label: "System Design" },
  { value: "oop", label: "Object-Oriented Programming" },
  { value: "web_dev", label: "Web Development" },
  { value: "databases", label: "Databases" },
  { value: "behavioral", label: "Behavioral" },
];

const DIFFICULTIES = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

const DURATIONS = [
  { value: 15, label: "15 min" },
  { value: 30, label: "30 min" },
  { value: 45, label: "45 min" },
];

interface MockInterviewSetupProps {
  onStart: (data: StartInterviewResponse) => void;
}

export function MockInterviewSetup({ onStart }: MockInterviewSetupProps) {
  const [topic, setTopic] = useState("python");
  const [difficulty, setDifficulty] = useState("medium");
  const [duration, setDuration] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await startInterview(topic, difficulty, duration);
      onStart(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start interview");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div className="flex items-center justify-between">
        <PageHeader title="Mock Interview" />
        <Link href="/interview">
          <Button variant="ghost" size="sm">← Back</Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2.5">
              <Brain className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle>Configure Your Interview</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Choose your topic, difficulty, and duration
              </p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Topic */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Topic</Label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {TOPICS.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setTopic(t.value)}
                  className={`rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors ${
                    topic === t.value
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border hover:border-primary/40 hover:bg-accent"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Difficulty */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Difficulty</Label>
            <div className="flex gap-2">
              {DIFFICULTIES.map((d) => (
                <button
                  key={d.value}
                  onClick={() => setDifficulty(d.value)}
                  className={`flex-1 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors ${
                    difficulty === d.value
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border hover:border-primary/40 hover:bg-accent"
                  }`}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          {/* Duration */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Duration</Label>
            <div className="flex gap-2">
              {DURATIONS.map((d) => (
                <button
                  key={d.value}
                  onClick={() => setDuration(d.value)}
                  className={`flex-1 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors ${
                    duration === d.value
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border hover:border-primary/40 hover:bg-accent"
                  }`}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <Button
            onClick={handleStart}
            disabled={loading}
            className="w-full"
            size="lg"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Starting...
              </>
            ) : (
              "Start Interview"
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
