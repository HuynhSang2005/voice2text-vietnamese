class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.bufferSize = 4096 // Send chunks of ~250ms at 16kHz
    this.buffer = new Float32Array(this.bufferSize)
    this.bytesWritten = 0
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0]
    if (!input || !input.length) return true

    const channelData = input[0] // Mono channel
    
    // Downsample and buffer logic would go here if input sample rate != 16000
    // But for simplicity and performance, we'll assume the AudioContext is set to 16000
    // or we handle simple buffering here.
    
    // We need to convert Float32 to Int16
    for (let i = 0; i < channelData.length; i++) {
      this.buffer[this.bytesWritten++] = channelData[i]

      // When buffer is full, flush it
      if (this.bytesWritten >= this.bufferSize) {
        this.flush()
      }
    }

    return true
  }

  flush() {
    const int16Data = new Int16Array(this.bytesWritten)
    for (let i = 0; i < this.bytesWritten; i++) {
      // Clamp and convert
      const s = Math.max(-1, Math.min(1, this.buffer[i]))
      int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
    }

    // Send to main thread
    this.port.postMessage(int16Data.buffer, [int16Data.buffer])
    
    // Reset buffer
    this.bytesWritten = 0
  }
}

registerProcessor('pcm-processor', PCMProcessor)
