"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Volume2, VolumeX, Loader2 } from "lucide-react";
import type { LociWalkthrough } from "@/types/loci";

interface WalkthroughPlayerProps {
  walkthrough: LociWalkthrough;
  fullNarration: string;
}

export function WalkthroughPlayer({ walkthrough, fullNarration }: WalkthroughPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);
  const [loading, setLoading] = useState(false);

  const handlePlayAudio = async () => {
    if (currentAudio) {
      currentAudio.pause();
      setCurrentAudio(null);
      setIsPlaying(false);
      return;
    }

    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/voice/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: fullNarration }),
      });

      if (!response.ok) throw new Error("TTS request failed");

      const blob = await response.blob();
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);

      audio.onended = () => {
        setIsPlaying(false);
        setCurrentAudio(null);
        URL.revokeObjectURL(audioUrl);
      };

      audio.onerror = () => {
        setIsPlaying(false);
        setCurrentAudio(null);
        URL.revokeObjectURL(audioUrl);
      };

      setCurrentAudio(audio);
      await audio.play();
      setIsPlaying(true);
    } catch (error) {
      console.error("Audio playback error:", error);
      alert("Failed to play audio. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{walkthrough.palace_theme}</CardTitle>
          <Button onClick={handlePlayAudio} disabled={loading} variant="outline">
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : isPlaying ? (
              <VolumeX className="h-4 w-4 mr-2" />
            ) : (
              <Volume2 className="h-4 w-4 mr-2" />
            )}
            {isPlaying ? "Stop Audio" : "Play Walkthrough"}
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="prose prose-sm max-w-none">
            <p className="text-muted-foreground italic">{walkthrough.introduction}</p>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-3">
        {walkthrough.locations.map((location) => (
          <Card key={location.position}>
            <CardHeader>
              <CardTitle className="text-base">
                {location.position}. {location.location_name}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-start gap-2">
                <span className="font-semibold text-sm text-primary">Item:</span>
                <span className="text-sm">{location.item}</span>
              </div>
              <div className="prose prose-sm max-w-none">
                <p className="text-muted-foreground">{location.vivid_image}</p>
                <p className="italic">{location.narration}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent className="pt-6">
          <p className="text-muted-foreground italic">{walkthrough.conclusion}</p>
        </CardContent>
      </Card>
    </div>
  );
}
