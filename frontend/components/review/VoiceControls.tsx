"use client";

import { Volume2, VolumeX, Mic, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface VoiceControlsProps {
  voiceEnabled: boolean;
  isSpeaking: boolean;
  isRecording: boolean;
  onToggleVoice: () => void;
  onStopSpeaking: () => void;
}

export function VoiceControls({
  voiceEnabled,
  isSpeaking,
  isRecording,
  onToggleVoice,
  onStopSpeaking,
}: VoiceControlsProps) {
  return (
    <div className="flex items-center gap-2">
      <Button
        type="button"
        variant={voiceEnabled ? "default" : "outline"}
        size="sm"
        onClick={onToggleVoice}
        className="gap-1.5"
        aria-label={voiceEnabled ? "Disable voice mode" : "Enable voice mode"}
      >
        {voiceEnabled ? (
          <>
            <Volume2 className="h-3.5 w-3.5" />
            Voice On
          </>
        ) : (
          <>
            <VolumeX className="h-3.5 w-3.5" />
            Voice Off
          </>
        )}
      </Button>

      {isSpeaking && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onStopSpeaking}
          className="gap-1.5 text-muted-foreground"
          aria-label="Stop speaking"
        >
          <VolumeX className="h-3.5 w-3.5" />
          Skip
        </Button>
      )}

      {isRecording && (
        <div className="flex items-center gap-1.5 text-sm text-red-500">
          <Mic className={cn("h-3.5 w-3.5 animate-pulse")} />
          <span className="animate-pulse">Listening...</span>
        </div>
      )}
    </div>
  );
}
