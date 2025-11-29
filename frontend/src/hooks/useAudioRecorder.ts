import { useRef, useCallback, useState } from 'react'

export interface AudioRecorderState {
  isRecording: boolean
  isInitialized: boolean
  error: string | null
  mediaStream: MediaStream | null
}

export interface UseAudioRecorderOptions {
  onAudioData?: (data: ArrayBuffer) => void
  onError?: (error: Error) => void
  sampleRate?: number
  /** Specific device ID to use for recording */
  deviceId?: string
}

/**
 * Custom hook for audio recording using AudioWorklet
 * Captures audio from microphone and converts to PCM Int16 format at 16kHz
 * 
 * @example
 * ```tsx
 * const { start, stop, isRecording } = useAudioRecorder({
 *   onAudioData: (buffer) => sendMessage(buffer),
 *   sampleRate: 16000,
 * })
 * ```
 */
export function useAudioRecorder(options: UseAudioRecorderOptions = {}) {
  const {
    onAudioData,
    onError,
    sampleRate = 16000,
    deviceId,
  } = options

  const [state, setState] = useState<AudioRecorderState>({
    isRecording: false,
    isInitialized: false,
    error: null,
    mediaStream: null,
  })

  // Refs for audio objects (persist across renders)
  const audioContextRef = useRef<AudioContext | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null)

  /**
   * Initialize AudioContext and AudioWorklet
   */
  const initialize = useCallback(async (): Promise<boolean> => {
    try {
      // Create AudioContext with target sample rate
      // Note: Browser may not support exact 16kHz, AudioWorklet handles resampling
      const audioContext = new AudioContext({
        sampleRate,
      })

      // Load AudioWorklet processor
      await audioContext.audioWorklet.addModule('/pcm-processor.js')

      audioContextRef.current = audioContext
      setState((prev) => ({ ...prev, isInitialized: true, error: null }))
      
      return true
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to initialize audio')
      setState((prev) => ({ ...prev, error: err.message }))
      onError?.(err)
      return false
    }
  }, [sampleRate, onError])

  /**
   * Start recording audio from microphone
   */
  const start = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, error: null }))

      // Initialize if needed
      if (!audioContextRef.current) {
        const success = await initialize()
        if (!success) return
      }

      const audioContext = audioContextRef.current!

      // Resume context if suspended (browser autoplay policy)
      if (audioContext.state === 'suspended') {
        await audioContext.resume()
      }

      // Request microphone access
      const audioConstraints: MediaTrackConstraints = {
        channelCount: 1, // Mono
        sampleRate, // Prefer 16kHz
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      }

      // Use specific device if provided
      if (deviceId) {
        audioConstraints.deviceId = { exact: deviceId }
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: audioConstraints,
      })

      mediaStreamRef.current = stream

      // Create source node from microphone
      const sourceNode = audioContext.createMediaStreamSource(stream)
      sourceNodeRef.current = sourceNode

      // Create AudioWorklet node
      const workletNode = new AudioWorkletNode(audioContext, 'pcm-processor')
      workletNodeRef.current = workletNode

      // Handle PCM data from worklet
      workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        if (event.data && onAudioData) {
          onAudioData(event.data)
        }
      }

      // Connect: Microphone -> Worklet
      sourceNode.connect(workletNode)
      // Note: We don't connect to destination (no playback needed)

      setState((prev) => ({ ...prev, isRecording: true, mediaStream: stream }))
    } catch (error) {
      let errorMessage = 'Failed to start recording'
      
      // Handle specific errors
      if (error instanceof DOMException) {
        if (error.name === 'NotAllowedError') {
          errorMessage = 'Microphone permission denied. Please allow microphone access.'
        } else if (error.name === 'NotFoundError') {
          errorMessage = 'No microphone found. Please connect a microphone.'
        }
      } else if (error instanceof Error) {
        errorMessage = error.message
      }

      const err = new Error(errorMessage)
      setState((prev) => ({ ...prev, error: errorMessage }))
      onError?.(err)
    }
  }, [initialize, sampleRate, deviceId, onAudioData, onError])

  /**
   * Stop recording and cleanup resources
   */
  const stop = useCallback(() => {
    // Disconnect worklet
    if (workletNodeRef.current) {
      workletNodeRef.current.port.onmessage = null
      workletNodeRef.current.disconnect()
      workletNodeRef.current = null
    }

    // Disconnect source
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect()
      sourceNodeRef.current = null
    }

    // Stop all media tracks
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop())
      mediaStreamRef.current = null
    }

    setState((prev) => ({ ...prev, isRecording: false, mediaStream: null }))
  }, [])

  /**
   * Cleanup all resources (call on unmount)
   */
  const cleanup = useCallback(() => {
    stop()

    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    setState({
      isRecording: false,
      isInitialized: false,
      error: null,
      mediaStream: null,
    })
  }, [stop])

  return {
    // State
    isRecording: state.isRecording,
    isInitialized: state.isInitialized,
    error: state.error,
    mediaStream: state.mediaStream,

    // Actions
    start,
    stop,
    cleanup,
    initialize,
  }
}
