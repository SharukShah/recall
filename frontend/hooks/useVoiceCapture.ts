"use client";

import { useState, useRef, useCallback, useEffect } from "react";

// Augment Window with webkit prefix
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

type SpeechRecognitionType = new () => {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

function getSpeechRecognition(): SpeechRecognitionType | null {
  if (typeof window === "undefined") return null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition || null;
}

export function useVoiceCapture() {
  const [isListening, setIsListening] = useState(false);
  const [interimText, setInterimText] = useState("");
  const [isSupported, setIsSupported] = useState(false);
  const recognitionRef = useRef<InstanceType<SpeechRecognitionType> | null>(null);
  const onTranscriptRef = useRef<((text: string) => void) | null>(null);

  // Check support after hydration to avoid server/client mismatch
  useEffect(() => {
    setIsSupported(getSpeechRecognition() !== null);
  }, []);

  const startListening = useCallback(async (onTranscript: (text: string) => void) => {
    const SpeechRecognition = getSpeechRecognition();
    if (!SpeechRecognition) return;

    // Explicitly request mic permission first — triggers browser prompt reliably
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Stop the stream immediately — SpeechRecognition manages its own
      stream.getTracks().forEach(t => t.stop());
    } catch {
      console.error("Microphone permission denied");
      return;
    }

    // Stop any existing session
    if (recognitionRef.current) {
      recognitionRef.current.abort();
    }

    onTranscriptRef.current = onTranscript;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          onTranscriptRef.current?.(transcript);
          setInterimText("");
        } else {
          interim += transcript;
        }
      }
      if (interim) setInterimText(interim);
    };

    recognition.onerror = (event: { error: string }) => {
      // no-speech: timed out waiting — restart automatically
      if (event.error === "no-speech") {
        try { recognition.start(); } catch { /* already started */ }
        return;
      }
      if (event.error !== "aborted") {
        console.error("Speech recognition error:", event.error);
      }
      setIsListening(false);
      setInterimText("");
    };

    recognition.onend = () => {
      // Auto-restart if user hasn't explicitly stopped
      if (recognitionRef.current === recognition) {
        try { recognition.start(); } catch { /* ignore */ }
        return;
      }
      setIsListening(false);
      setInterimText("");
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, []);

  const stopListening = useCallback(() => {
    const rec = recognitionRef.current;
    recognitionRef.current = null; // clear ref first so onend doesn't auto-restart
    rec?.stop();
    setIsListening(false);
    setInterimText("");
  }, []);

  return { isListening, interimText, isSupported, startListening, stopListening };
}
