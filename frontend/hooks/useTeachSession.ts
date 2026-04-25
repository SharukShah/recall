"use client";

import { useState, useCallback } from "react";
import { startTeachSession, respondToTeach } from "@/lib/api";
import type { TeachStartResponse, TeachRespondResponse } from "@/types/api";

type TeachPhase = "idle" | "loading" | "teaching" | "feedback" | "complete";

interface TeachState {
  phase: TeachPhase;
  sessionId: string | null;
  topic: string;
  totalChunks: number;
  currentChunk: number;
  chunkTitle: string;
  chunkContent: string;
  chunkAnalogy: string | null;
  recallQuestion: string;
  feedback: string | null;
  score: "correct" | "partial" | "wrong" | null;
  summary: string | null;
  captureId: string | null;
  error: string | null;
}

const initialState: TeachState = {
  phase: "idle",
  sessionId: null,
  topic: "",
  totalChunks: 0,
  currentChunk: 0,
  chunkTitle: "",
  chunkContent: "",
  chunkAnalogy: null,
  recallQuestion: "",
  feedback: null,
  score: null,
  summary: null,
  captureId: null,
  error: null,
};

export function useTeachSession() {
  const [state, setState] = useState<TeachState>(initialState);

  const start = useCallback(async (topic: string) => {
    setState((s) => ({ ...s, phase: "loading", error: null, topic }));
    try {
      const res: TeachStartResponse = await startTeachSession(topic);
      setState({
        phase: "teaching",
        sessionId: res.session_id,
        topic: res.topic,
        totalChunks: res.total_chunks,
        currentChunk: res.current_chunk,
        chunkTitle: res.chunk_title,
        chunkContent: res.chunk_content,
        chunkAnalogy: res.chunk_analogy,
        recallQuestion: res.recall_question,
        feedback: null,
        score: null,
        summary: null,
        captureId: null,
        error: null,
      });
    } catch (err) {
      setState((s) => ({
        ...s,
        phase: "idle",
        error: err instanceof Error ? err.message : "Failed to start session.",
      }));
    }
  }, []);

  const respond = useCallback(async (answer: string) => {
    if (!state.sessionId) return;
    setState((s) => ({ ...s, phase: "loading", error: null }));
    try {
      const res: TeachRespondResponse = await respondToTeach(state.sessionId, answer);
      if (res.is_complete) {
        setState((s) => ({
          ...s,
          phase: "complete",
          feedback: res.feedback,
          score: res.score,
          summary: res.summary ?? null,
          captureId: res.capture_id ?? null,
        }));
      } else {
        setState((s) => ({
          ...s,
          phase: "feedback",
          feedback: res.feedback,
          score: res.score,
          currentChunk: res.current_chunk ?? s.currentChunk + 1,
          chunkTitle: res.chunk_title ?? "",
          chunkContent: res.chunk_content ?? "",
          chunkAnalogy: res.chunk_analogy ?? null,
          recallQuestion: res.recall_question ?? "",
        }));
      }
    } catch (err) {
      setState((s) => ({
        ...s,
        phase: "teaching",
        error: err instanceof Error ? err.message : "Failed to evaluate answer.",
      }));
    }
  }, [state.sessionId]);

  const continueToNext = useCallback(() => {
    setState((s) => ({ ...s, phase: "teaching", feedback: null, score: null }));
  }, []);

  const reset = useCallback(() => {
    setState(initialState);
  }, []);

  return { ...state, start, respond, continueToNext, reset };
}
