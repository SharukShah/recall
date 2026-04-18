"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { speakText } from "@/lib/audio";

export function useVoiceReview() {
  const [voiceEnabled, setVoiceEnabled] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("recall-voice-enabled") === "true";
  });
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const stopFnRef = useRef<(() => void) | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const recognitionRef = useRef<ReturnType<typeof createRecognition> | null>(null);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      stopFnRef.current?.();
      recognitionRef.current?.abort();
    };
  }, []);

  // C2/F9 fix: cancel previous speak before starting new one
  const speak = useCallback(
    async (text: string) => {
      if (!voiceEnabled) return;

      // Cancel any in-flight previous speak
      abortRef.current?.abort();
      stopFnRef.current?.();

      const controller = new AbortController();
      abortRef.current = controller;
      setIsSpeaking(true);

      try {
        const { promise, stop } = await speakText(text, "nova", controller.signal);
        if (controller.signal.aborted) return;
        stopFnRef.current = stop;
        await promise;
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        console.error("TTS failed:", err);
      } finally {
        if (!controller.signal.aborted) {
          stopFnRef.current = null;
          setIsSpeaking(false);
        }
      }
    },
    [voiceEnabled]
  );

  const stopSpeaking = useCallback(() => {
    abortRef.current?.abort();
    stopFnRef.current?.();
    stopFnRef.current = null;
    setIsSpeaking(false);
  }, []);

  // C3/F10 fix: abort previous recognition before starting new
  // F13 fix: wrap recognition.start() in try-catch
  const listenForAnswer = useCallback((): Promise<string> => {
    return new Promise((resolve) => {
      // Abort any existing recognition first
      if (recognitionRef.current) {
        recognitionRef.current.abort();
        recognitionRef.current = null;
      }

      const recognition = createRecognition();
      if (!recognition) {
        resolve("");
        return;
      }

      recognitionRef.current = recognition;
      let finalTranscript = "";
      setIsRecording(true);

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript + " ";
          }
        }
      };

      recognition.onerror = () => {
        setIsRecording(false);
        recognitionRef.current = null;
        resolve(finalTranscript.trim());
      };

      recognition.onend = () => {
        setIsRecording(false);
        recognitionRef.current = null;
        resolve(finalTranscript.trim());
      };

      try {
        recognition.start();
      } catch {
        // Permission denied or other sync error
        setIsRecording(false);
        recognitionRef.current = null;
        resolve("");
      }
    });
  }, []);

  const stopRecording = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const toggle = useCallback(() => {
    setVoiceEnabled((prev) => {
      const next = !prev;
      localStorage.setItem("recall-voice-enabled", String(next));
      return next;
    });
    // Stop any ongoing speech/recording when toggling
    abortRef.current?.abort();
    stopFnRef.current?.();
    recognitionRef.current?.abort();
    setIsSpeaking(false);
    setIsRecording(false);
  }, []);

  // F12: expose whether SpeechRecognition is available
  const isSpeechSupported = typeof window !== "undefined" &&
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Boolean((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);

  return {
    voiceEnabled,
    isSpeaking,
    isRecording,
    isSpeechSupported,
    speak,
    stopSpeaking,
    listenForAnswer,
    stopRecording,
    toggle,
  };
}

// --- Helpers ---

interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

function createRecognition() {
  if (typeof window === "undefined") return null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  if (!SpeechRecognition) return null;

  const recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = false;
  recognition.lang = "en-US";
  return recognition;
}
