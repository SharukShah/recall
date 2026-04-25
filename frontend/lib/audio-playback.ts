/**
 * Streaming PCM playback via AudioContext.
 * Queues incoming PCM chunks and plays them with gapless buffering.
 */

export class PCMPlayer {
  private context: AudioContext | null = null;
  private nextStartTime = 0;
  private sampleRate: number;
  private playing = false;
  private gainNode: GainNode | null = null;

  constructor(sampleRate = 24000) {
    this.sampleRate = sampleRate;
  }

  init(): void {
    if (this.context) return;
    this.context = new AudioContext({ sampleRate: this.sampleRate });
    this.gainNode = this.context.createGain();
    this.gainNode.connect(this.context.destination);
    this.nextStartTime = 0;
    this.playing = true;
  }

  /**
   * Feed raw PCM Int16 LE bytes for playback.
   * Schedules them for gapless consecutive playback.
   */
  feed(pcmData: ArrayBuffer): void {
    if (!this.context || !this.gainNode || !this.playing) return;

    const int16 = new Int16Array(pcmData);
    if (int16.length === 0) return;

    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768;
    }

    const audioBuffer = this.context.createBuffer(1, float32.length, this.sampleRate);
    audioBuffer.getChannelData(0).set(float32);

    const source = this.context.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.gainNode);

    const currentTime = this.context.currentTime;
    const startTime = Math.max(currentTime, this.nextStartTime);
    source.start(startTime);

    this.nextStartTime = startTime + audioBuffer.duration;
  }

  /**
   * Stop playback and flush all scheduled audio.
   */
  stop(): void {
    this.playing = false;
    if (this.context) {
      this.context.close().catch(() => {});
      this.context = null;
      this.gainNode = null;
    }
    this.nextStartTime = 0;
  }

  /**
   * Flush queued audio (for barge-in) without destroying context.
   * Disconnects and reconnects gain node to cancel all scheduled sources.
   */
  flush(): void {
    if (this.context && this.gainNode) {
      this.gainNode.disconnect();
      this.gainNode = this.context.createGain();
      this.gainNode.connect(this.context.destination);
      this.nextStartTime = this.context.currentTime;
    }
  }

  isPlaying(): boolean {
    return this.playing;
  }
}
