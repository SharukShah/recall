"use client";

import { useState } from "react";
import { GraduationCap, Loader2, RotateCcw, CheckCircle2, XCircle, AlertCircle, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTeachSession } from "@/hooks/useTeachSession";
import { ChunkCard } from "./ChunkCard";
import { RecallCheck } from "./RecallCheck";

export function TeachSession() {
  const session = useTeachSession();
  const [topic, setTopic] = useState("");

  const handleStart = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    session.start(topic.trim());
  };

  // Idle state — topic input
  if (session.phase === "idle") {
    return (
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <GraduationCap className="h-12 w-12 text-primary mx-auto" />
          <h2 className="text-lg font-semibold">Teach Me Mode</h2>
          <p className="text-sm text-muted-foreground">
            Enter a topic and AI will teach you using chunking, elaboration, and active recall.
          </p>
        </div>

        <form onSubmit={handleStart} className="space-y-4">
          <Input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., How does DNS work?"
            maxLength={500}
            autoFocus
          />
          <Button type="submit" className="w-full" size="lg" disabled={!topic.trim()}>
            <GraduationCap className="mr-2 h-4 w-4" />
            Start Learning
          </Button>
        </form>

        {session.error && (
          <p className="text-sm text-destructive text-center">{session.error}</p>
        )}
      </div>
    );
  }

  // Loading state
  if (session.phase === "loading") {
    return (
      <div className="flex flex-col items-center gap-4 py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">
          {session.sessionId ? "Evaluating your answer..." : "Generating teaching plan..."}
        </p>
      </div>
    );
  }

  // Feedback state — show feedback + continue button
  if (session.phase === "feedback") {
    return (
      <div className="space-y-4">
        <FeedbackDisplay feedback={session.feedback!} score={session.score!} />
        <Button onClick={session.continueToNext} className="w-full" size="lg">
          <ArrowRight className="mr-2 h-4 w-4" />
          Continue to Next Chunk
        </Button>
      </div>
    );
  }

  // Complete state — session finished
  if (session.phase === "complete") {
    return (
      <div className="space-y-4">
        {session.feedback && session.score && (
          <FeedbackDisplay feedback={session.feedback} score={session.score} />
        )}
        <Card>
          <CardContent className="pt-6 space-y-4 text-center">
            <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto" />
            <h2 className="text-lg font-semibold">Lesson Complete!</h2>
            {session.summary && (
              <p className="text-sm text-muted-foreground">{session.summary}</p>
            )}
            {session.captureId && (
              <Badge variant="secondary">
                Auto-captured for review
              </Badge>
            )}
          </CardContent>
        </Card>
        <Button onClick={session.reset} variant="outline" className="w-full">
          <RotateCcw className="mr-2 h-4 w-4" />
          Learn Something Else
        </Button>
      </div>
    );
  }

  // Teaching state — show chunk + recall check
  return (
    <div className="space-y-4">
      <ChunkCard
        title={session.chunkTitle}
        content={session.chunkContent}
        analogy={session.chunkAnalogy}
        chunkIndex={session.currentChunk}
        totalChunks={session.totalChunks}
      />
      <RecallCheck
        question={session.recallQuestion}
        onSubmit={session.respond}
        isLoading={false}
      />
      {session.error && (
        <p className="text-sm text-destructive text-center">{session.error}</p>
      )}
    </div>
  );
}

function FeedbackDisplay({ feedback, score }: { feedback: string; score: "correct" | "partial" | "wrong" }) {
  const config = {
    correct: { icon: CheckCircle2, color: "text-green-500", bg: "bg-green-50 border-green-200", label: "Correct" },
    partial: { icon: AlertCircle, color: "text-yellow-500", bg: "bg-yellow-50 border-yellow-200", label: "Partial" },
    wrong: { icon: XCircle, color: "text-red-500", bg: "bg-red-50 border-red-200", label: "Needs Review" },
  }[score];
  const Icon = config.icon;

  return (
    <div className={`p-4 rounded-lg border ${config.bg}`}>
      <div className="flex items-start gap-3">
        <Icon className={`h-5 w-5 mt-0.5 shrink-0 ${config.color}`} />
        <div className="space-y-1">
          <p className="text-sm font-medium">{config.label}</p>
          <p className="text-sm">{feedback}</p>
        </div>
      </div>
    </div>
  );
}
