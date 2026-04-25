"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { PCMPlayer } from "@/lib/audio-playback";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export type VoiceStatus = "idle" | "connecting" | "ready" | "active" | "error";

export interface TranscriptEntry {
  role: "user" | "agent";
  text: string;
  timestamp: number;
}

export interface ModeState {
  state: string;
  detail?: Record<string, unknown>;
}

export interface VoiceAgentOptions {
  sessionId?: string;
}

export interface FunctionResult {
  name: string;
  result: Record<string, unknown>;
}

export function useVoiceAgent() {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [modeState, setModeState] = useState<ModeState>({ state: "idle" });
  const [error, setError] = useState<string | null>(null);
  const [sessionDuration, setSessionDuration] = useState(0);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [lastFunctionResult, setLastFunctionResult] = useState<FunctionResult | null>(null);
  const [sessionSummary, setSessionSummary] = useState<Record<string, unknown> | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const disconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const statusRef = useRef(status);
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const playerRef = useRef<PCMPlayer | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  // Duration timer
  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const startTimer = useCallback(() => {
    startTimeRef.current = Date.now();
    setSessionDuration(0);
    timerRef.current = setInterval(() => {
      setSessionDuration(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const cleanup = useCallback(() => {
    stopTimer();

    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (playerRef.current) {
      playerRef.current.stop();
      playerRef.current = null;
    }
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close();
      }
      wsRef.current = null;
    }
  }, [stopTimer]);

  // Cleanup on unmount
  useEffect(() => {
    return () => cleanup();
  }, [cleanup]);

  const connect = useCallback(
    async (options?: VoiceAgentOptions) => {
      // Reset state
      setError(null);
      setTranscript([]);
      setModeState({ state: "idle" });
      setSessionSummary(null);
      setLastFunctionResult(null);
      setIsAgentSpeaking(false);
      setIsUserSpeaking(false);
      setStatus("connecting");

      try {
        // Request mic permission
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            sampleRate: 16000,
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
          },
        });
        streamRef.current = stream;

        // Set up AudioContext + Worklet for mic capture
        const audioCtx = new AudioContext({ sampleRate: 16000 });
        audioContextRef.current = audioCtx;

        await audioCtx.audioWorklet.addModule("/audio-capture-processor.js");

        const source = audioCtx.createMediaStreamSource(stream);
        const workletNode = new AudioWorkletNode(audioCtx, "audio-capture-processor");
        workletNodeRef.current = workletNode;
        source.connect(workletNode);
        workletNode.connect(audioCtx.destination);

        // Set up PCM player for TTS output
        const player = new PCMPlayer(24000);
        player.init();
        playerRef.current = player;

        // Build WebSocket URL
        const params = new URLSearchParams();
        if (options?.sessionId) params.set("session_id", options.sessionId);
        const qs = params.toString();
        const wsUrl = `${WS_BASE}/ws/voice${qs ? `?${qs}` : ""}`;

        // Open WebSocket
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.binaryType = "arraybuffer";

        ws.onopen = () => {
          // Start sending mic audio to WS
          workletNode.port.onmessage = (event: MessageEvent) => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(event.data);
            }
          };
        };

        ws.onmessage = (event: MessageEvent) => {
          if (event.data instanceof ArrayBuffer) {
            // Binary TTS audio from Deepgram
            player.feed(event.data);
            setIsAgentSpeaking(true);
          } else {
            // JSON message
            try {
              const data = JSON.parse(event.data as string);
              handleJsonMessage(data);
            } catch {
              // ignore parse errors
            }
          }
        };

        ws.onerror = () => {
          setError("WebSocket connection failed");
          setStatus("error");
          cleanup();
        };

        ws.onclose = (e) => {
          if (statusRef.current !== "error") {
            setStatus("idle");
          }
          if (disconnectTimeoutRef.current) {
            clearTimeout(disconnectTimeoutRef.current);
            disconnectTimeoutRef.current = null;
          }
          cleanup();
        };
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to start voice session";
        setError(msg);
        setStatus("error");
        cleanup();
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const handleJsonMessage = useCallback(
    (data: Record<string, unknown>) => {
      const type = data.type as string;

      switch (type) {
        case "ready":
          setStatus("active");
          startTimer();
          break;

        case "transcript":
          setTranscript((prev) => [
            ...prev,
            {
              role: data.role as "user" | "agent",
              text: data.text as string,
              timestamp: Date.now(),
            },
          ]);
          break;

        case "status": {
          const state = data.state as string;
          setModeState({ state, detail: data.detail as Record<string, unknown> });
          if (state === "user_speaking") {
            setIsUserSpeaking(true);
            setIsAgentSpeaking(false);
            // Flush audio on barge-in
            playerRef.current?.flush();
          } else if (state === "agent_done_speaking") {
            setIsAgentSpeaking(false);
          } else if (state === "thinking") {
            setIsAgentSpeaking(false);
            setIsUserSpeaking(false);
          }
          break;
        }

        case "function_result":
          setLastFunctionResult({
            name: data.name as string,
            result: data.result as Record<string, unknown>,
          });
          break;

        case "session_end":
          setSessionSummary(data.summary as Record<string, unknown>);
          setStatus("idle");
          stopTimer();
          break;

        case "error":
          setError(data.message as string);
          setStatus("error");
          stopTimer();
          break;
      }
    },
    [startTimer, stopTimer],
  );

  const disconnect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "end" }));
      // Give server time to respond, then close
      disconnectTimeoutRef.current = setTimeout(() => cleanup(), 2000);
    } else {
      cleanup();
    }
    setStatus("idle");
  }, [cleanup]);

  return {
    status,
    isAgentSpeaking,
    isUserSpeaking,
    transcript,
    modeState,
    error,
    sessionDuration,
    lastFunctionResult,
    sessionSummary,
    connect,
    disconnect,
  };
}
