"use client";

import { Mic, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useVoiceCapture } from "@/hooks/useVoiceCapture";

interface VoiceCaptureButtonProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

export function VoiceCaptureButton({ onTranscript, disabled }: VoiceCaptureButtonProps) {
  const { isListening, interimText, isSupported, startListening, stopListening } =
    useVoiceCapture();

  if (!isSupported) return null;

  const toggle = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening(onTranscript);
    }
  };

  return (
    <div className="space-y-2">
      <Button
        type="button"
        variant={isListening ? "destructive" : "outline"}
        size="sm"
        onClick={toggle}
        disabled={disabled}
        className={cn(
          "gap-2",
          isListening && "animate-pulse"
        )}
        aria-label={isListening ? "Stop recording" : "Start voice capture"}
      >
        {isListening ? (
          <>
            <MicOff className="h-4 w-4" />
            Stop Recording
          </>
        ) : (
          <>
            <Mic className="h-4 w-4" />
            Voice Capture
          </>
        )}
      </Button>
      {isListening && interimText && (
        <p className="text-xs text-muted-foreground italic animate-pulse">
          {interimText}
        </p>
      )}
    </div>
  );
}
