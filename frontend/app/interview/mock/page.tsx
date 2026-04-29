"use client";

import { useState } from "react";
import { MockInterviewSetup } from "@/components/interview/MockInterviewSetup";
import { MockInterviewSession } from "@/components/interview/MockInterviewSession";
import { InterviewResultSummary } from "@/components/interview/InterviewResultSummary";
import type { StartInterviewResponse, InterviewSummary } from "@/types/api";

type Phase = "setup" | "session" | "results";

export default function MockInterviewPage() {
  const [phase, setPhase] = useState<Phase>("setup");
  const [interviewData, setInterviewData] = useState<StartInterviewResponse | null>(null);
  const [summary, setSummary] = useState<InterviewSummary | null>(null);

  const handleStart = (data: StartInterviewResponse) => {
    setInterviewData(data);
    setPhase("session");
  };

  const handleComplete = (result: InterviewSummary) => {
    setSummary(result);
    setPhase("results");
  };

  const handleRestart = () => {
    setInterviewData(null);
    setSummary(null);
    setPhase("setup");
  };

  if (phase === "session" && interviewData) {
    return <MockInterviewSession interview={interviewData} onComplete={handleComplete} />;
  }

  if (phase === "results" && summary) {
    return <InterviewResultSummary summary={summary} onBack={handleRestart} />;
  }

  return <MockInterviewSetup onStart={handleStart} />;
}
