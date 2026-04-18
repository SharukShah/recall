const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Fetch TTS audio from the backend and return as a Blob URL.
 * Includes a timeout via AbortController (default 15s).
 */
export async function fetchTTSAudio(
  text: string,
  voice = "nova",
  timeoutMs = 15000
): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    // Truncate to backend's 5000-char limit
    const truncated = text.slice(0, 5000);
    const res = await fetch(`${API_BASE}/api/voice/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: truncated, voice }),
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`TTS request failed: ${res.status}`);
    }
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Play audio from a Blob URL. Returns a promise that resolves when playback
 * ends AND a stop function for early termination.
 * stop() properly resolves the promise (fixes dangling promise on pause).
 */
export function playAudio(blobUrl: string): { promise: Promise<void>; stop: () => void } {
  const audio = new Audio(blobUrl);
  let resolved = false;
  let doResolve: (() => void) | null = null;

  const finish = () => {
    if (!resolved) {
      resolved = true;
      URL.revokeObjectURL(blobUrl);
      doResolve?.();
    }
  };

  const promise = new Promise<void>((resolve) => {
    doResolve = resolve;
    audio.onended = () => finish();
    audio.onerror = () => finish();
    audio.play().catch(() => finish());
  });

  const stop = () => {
    audio.pause();
    audio.currentTime = 0;
    audio.src = "";
    finish();
  };

  return { promise, stop };
}

/**
 * Speak text via TTS: fetch audio from backend, play it.
 * Accepts an AbortSignal for external cancellation.
 */
export async function speakText(
  text: string,
  voice = "nova",
  signal?: AbortSignal
): Promise<{ promise: Promise<void>; stop: () => void }> {
  if (signal?.aborted) {
    return { promise: Promise.resolve(), stop: () => {} };
  }

  const blobUrl = await fetchTTSAudio(text, voice);

  if (signal?.aborted) {
    URL.revokeObjectURL(blobUrl);
    return { promise: Promise.resolve(), stop: () => {} };
  }

  const playback = playAudio(blobUrl);

  if (signal) {
    const onAbort = () => playback.stop();
    signal.addEventListener("abort", onAbort, { once: true });
    playback.promise.then(() => signal.removeEventListener("abort", onAbort));
  }

  return playback;
}
