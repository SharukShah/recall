/**
 * AudioWorklet processor for capturing mic input as 16kHz mono PCM Int16.
 * Loaded via: audioContext.audioWorklet.addModule('/audio-capture-processor.js')
 */
class AudioCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._bufferSize = 2048;
    this._buffer = new Float32Array(this._bufferSize);
    this._bufferIndex = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channelData = input[0]; // mono channel

    for (let i = 0; i < channelData.length; i++) {
      this._buffer[this._bufferIndex++] = channelData[i];

      if (this._bufferIndex >= this._bufferSize) {
        // Downsample from audioContext.sampleRate to 16000
        const downsampled = this._downsample(this._buffer, sampleRate, 16000);
        // Convert to Int16
        const int16 = this._floatToInt16(downsampled);
        // Send to main thread
        this.port.postMessage(int16.buffer, [int16.buffer]);
        this._buffer = new Float32Array(this._bufferSize);
        this._bufferIndex = 0;
      }
    }

    return true;
  }

  _downsample(buffer, fromRate, toRate) {
    if (fromRate === toRate) {
      return buffer;
    }
    const ratio = fromRate / toRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    for (let i = 0; i < newLength; i++) {
      const srcIndex = i * ratio;
      const srcIndexFloor = Math.floor(srcIndex);
      const srcIndexCeil = Math.min(srcIndexFloor + 1, buffer.length - 1);
      const frac = srcIndex - srcIndexFloor;
      result[i] = buffer[srcIndexFloor] * (1 - frac) + buffer[srcIndexCeil] * frac;
    }
    return result;
  }

  _floatToInt16(float32Array) {
    const int16 = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return int16;
  }
}

registerProcessor("audio-capture-processor", AudioCaptureProcessor);
