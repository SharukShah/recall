"use client";

import { Volume2, VolumeX, Mic } from "lucide-react";
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
        className={cn(
          "gap-1.5 text-xs",
          voiceEnabled && "bg-primary shadow-sm"
        )}
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
            Voice
          </>
        )}
      </Button>

      {isSpeaking && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onStopSpeaking}
          className="gap-1.5 text-xs text-muted-foreground"
          aria-label="Stop speaking"
        >
          <VolumeX className="h-3.5 w-3.5" />
          Skip
        </Button>
      )}

      {isRecording && (
        <div className="flex items-center gap-1.5 text-xs">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
          </span>
          <span className="text-red-500 font-medium">Listening...</span>
        </div>
      )}
    </div>
  );
}
