/**
 * Audio utility functions for PCM processing and audio handling
 */

// Target audio configuration
export const AUDIO_CONFIG = {
  sampleRate: 16000,
  channels: 1,
  bitsPerSample: 16,
} as const

/**
 * Convert Float32 audio samples to Int16
 * Float32 range: -1.0 to 1.0
 * Int16 range: -32768 to 32767
 */
export function float32ToInt16(float32Array: Float32Array): Int16Array {
  const int16Array = new Int16Array(float32Array.length)
  
  for (let i = 0; i < float32Array.length; i++) {
    // Clamp to [-1, 1] range
    const clamped = Math.max(-1, Math.min(1, float32Array[i]))
    // Convert to Int16
    int16Array[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7FFF
  }
  
  return int16Array
}

/**
 * Convert Int16 audio samples to Float32
 */
export function int16ToFloat32(int16Array: Int16Array): Float32Array {
  const float32Array = new Float32Array(int16Array.length)
  
  for (let i = 0; i < int16Array.length; i++) {
    float32Array[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7FFF)
  }
  
  return float32Array
}

/**
 * Calculate RMS (Root Mean Square) volume from audio samples
 * Returns a value between 0 and 1
 */
export function calculateRmsVolume(samples: Float32Array | Int16Array): number {
  if (samples.length === 0) return 0
  
  let sum = 0
  const isInt16 = samples instanceof Int16Array
  
  for (let i = 0; i < samples.length; i++) {
    const sample = isInt16 ? samples[i] / 0x7FFF : samples[i]
    sum += sample * sample
  }
  
  return Math.sqrt(sum / samples.length)
}

/**
 * Calculate peak volume from audio samples
 * Returns a value between 0 and 1
 */
export function calculatePeakVolume(samples: Float32Array | Int16Array): number {
  if (samples.length === 0) return 0
  
  let peak = 0
  const isInt16 = samples instanceof Int16Array
  
  for (let i = 0; i < samples.length; i++) {
    const sample = Math.abs(isInt16 ? samples[i] / 0x7FFF : samples[i])
    if (sample > peak) peak = sample
  }
  
  return peak
}

/**
 * Downsample audio from source sample rate to target sample rate
 * Uses simple linear interpolation
 */
export function downsample(
  samples: Float32Array,
  sourceSampleRate: number,
  targetSampleRate: number = AUDIO_CONFIG.sampleRate
): Float32Array {
  if (sourceSampleRate === targetSampleRate) {
    return samples
  }
  
  if (sourceSampleRate < targetSampleRate) {
    console.warn('Upsampling not recommended, returning original')
    return samples
  }
  
  const ratio = sourceSampleRate / targetSampleRate
  const newLength = Math.floor(samples.length / ratio)
  const result = new Float32Array(newLength)
  
  for (let i = 0; i < newLength; i++) {
    const srcIndex = i * ratio
    const srcIndexFloor = Math.floor(srcIndex)
    const srcIndexCeil = Math.min(srcIndexFloor + 1, samples.length - 1)
    const fraction = srcIndex - srcIndexFloor
    
    // Linear interpolation
    result[i] = samples[srcIndexFloor] * (1 - fraction) + samples[srcIndexCeil] * fraction
  }
  
  return result
}

/**
 * Check if browser supports AudioWorklet
 */
export function supportsAudioWorklet(): boolean {
  return typeof AudioWorkletNode !== 'undefined'
}

/**
 * Check if browser supports getUserMedia
 */
export function supportsGetUserMedia(): boolean {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
}

/**
 * Get audio constraints for getUserMedia
 */
export function getAudioConstraints(deviceId?: string): MediaStreamConstraints {
  const audioConstraints: MediaTrackConstraints = {
    channelCount: AUDIO_CONFIG.channels,
    echoCancellation: true,
    autoGainControl: true,
    noiseSuppression: true,
  }
  
  if (deviceId) {
    audioConstraints.deviceId = { exact: deviceId }
  }
  
  return {
    audio: audioConstraints,
    video: false,
  }
}

/**
 * Format bytes to human readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

/**
 * Format duration in seconds to mm:ss
 */
export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}
