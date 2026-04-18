"use client";

import { useReducer, useCallback, useEffect, useRef } from "react";
import { getDueQuestions, evaluateAnswer, rateQuestion } from "@/lib/api";
import type { ReviewQuestion, EvaluateResponse } from "@/types/api";

export type ReviewPhase = "loading" | "question" | "evaluating" | "feedback" | "rating" | "complete";

export interface ReviewSessionState {
  questions: ReviewQuestion[];
  currentIndex: number;
  phase: ReviewPhase;
  currentAnswer: string;
  evaluation: EvaluateResponse | null;
  sessionStats: {
    total: number;
    answered: number;
    ratings: Record<1 | 2 | 3 | 4, number>;
    startTime: number;
  };
  error: string | null;
}

type ReviewAction =
  | { type: "LOAD_QUESTIONS"; questions: ReviewQuestion[] }
  | { type: "LOAD_EMPTY" }
  | { type: "SET_ANSWER"; answer: string }
  | { type: "START_EVALUATE" }
  | { type: "EVALUATE_SUCCESS"; evaluation: EvaluateResponse }
  | { type: "EVALUATE_ERROR"; error: string }
  | { type: "START_RATE" }
  | { type: "RATE_SUCCESS"; rating: 1 | 2 | 3 | 4 }
  | { type: "RATE_ERROR"; error: string }
  | { type: "END_SESSION" }
  | { type: "SET_ERROR"; error: string };

const initialState: ReviewSessionState = {
  questions: [],
  currentIndex: 0,
  phase: "loading",
  currentAnswer: "",
  evaluation: null,
  sessionStats: {
    total: 0,
    answered: 0,
    ratings: { 1: 0, 2: 0, 3: 0, 4: 0 },
    startTime: Date.now(),
  },
  error: null,
};

function reducer(state: ReviewSessionState, action: ReviewAction): ReviewSessionState {
  switch (action.type) {
    case "LOAD_QUESTIONS":
      return {
        ...state,
        questions: action.questions,
        phase: action.questions.length > 0 ? "question" : "complete",
        currentIndex: 0,
        sessionStats: {
          ...state.sessionStats,
          total: action.questions.length,
          startTime: Date.now(),
        },
        error: null,
      };
    case "LOAD_EMPTY":
      return { ...state, phase: "complete", questions: [], error: null };
    case "SET_ANSWER":
      return { ...state, currentAnswer: action.answer };
    case "START_EVALUATE":
      return { ...state, phase: "evaluating", error: null };
    case "EVALUATE_SUCCESS":
      return { ...state, phase: "feedback", evaluation: action.evaluation, error: null };
    case "EVALUATE_ERROR":
      return { ...state, phase: "feedback", error: action.error, evaluation: null };
    case "START_RATE":
      return { ...state, phase: "rating", error: null };
    case "RATE_SUCCESS": {
      const newRatings = { ...state.sessionStats.ratings };
      newRatings[action.rating] += 1;
      const newAnswered = state.sessionStats.answered + 1;
      const nextIndex = state.currentIndex + 1;
      const isComplete = nextIndex >= state.questions.length;
      return {
        ...state,
        currentIndex: isComplete ? state.currentIndex : nextIndex,
        phase: isComplete ? "complete" : "question",
        currentAnswer: "",
        evaluation: null,
        sessionStats: {
          ...state.sessionStats,
          answered: newAnswered,
          ratings: newRatings,
        },
        error: null,
      };
    }
    case "RATE_ERROR":
      return { ...state, phase: "feedback", error: action.error };
    case "END_SESSION":
      return { ...state, phase: "complete" };
    case "SET_ERROR":
      return { ...state, error: action.error };
    default:
      return state;
  }
}

export function useReviewSession() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const isSubmitting = useRef(false);

  const loadQuestions = useCallback(async () => {
    try {
      const data = await getDueQuestions(20);
      if (data.questions.length === 0) {
        dispatch({ type: "LOAD_EMPTY" });
      } else {
        dispatch({ type: "LOAD_QUESTIONS", questions: data.questions });
      }
    } catch (err) {
      dispatch({ type: "SET_ERROR", error: err instanceof Error ? err.message : "Failed to load questions" });
    }
  }, []);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  const setAnswer = useCallback((answer: string) => {
    dispatch({ type: "SET_ANSWER", answer });
  }, []);

  const checkAnswer = useCallback(async () => {
    const question = state.questions[state.currentIndex];
    if (!question || !state.currentAnswer.trim() || isSubmitting.current) return;

    isSubmitting.current = true;
    dispatch({ type: "START_EVALUATE" });
    try {
      const evaluation = await evaluateAnswer({
        question_id: question.question_id,
        user_answer: state.currentAnswer,
      });
      dispatch({ type: "EVALUATE_SUCCESS", evaluation });
    } catch (err) {
      dispatch({
        type: "EVALUATE_ERROR",
        error: err instanceof Error ? err.message : "Evaluation failed",
      });
    } finally {
      isSubmitting.current = false;
    }
  }, [state.questions, state.currentIndex, state.currentAnswer]);

  const submitRating = useCallback(
    async (rating: 1 | 2 | 3 | 4) => {
      const question = state.questions[state.currentIndex];
      if (!question || isSubmitting.current) return;

      isSubmitting.current = true;
      dispatch({ type: "START_RATE" });
      try {
        await rateQuestion({
          question_id: question.question_id,
          rating,
          user_answer: state.currentAnswer,
          ai_feedback: state.evaluation?.feedback,
        });
        dispatch({ type: "RATE_SUCCESS", rating });
      } catch (err) {
        dispatch({
          type: "RATE_ERROR",
          error: err instanceof Error ? err.message : "Rating failed",
        });
      } finally {
        isSubmitting.current = false;
      }
    },
    [state.questions, state.currentIndex, state.currentAnswer, state.evaluation]
  );

  const endSession = useCallback(() => {
    dispatch({ type: "END_SESSION" });
  }, []);

  const currentQuestion = state.questions[state.currentIndex] ?? null;

  return {
    state,
    currentQuestion,
    setAnswer,
    checkAnswer,
    submitRating,
    endSession,
    retryLoad: loadQuestions,
  };
}
