import { useState, useRef, useCallback, useEffect } from 'react'
import { useAppStore } from '@/store'
import { useAudioContext } from './use-audio-context'
import { getAudioConstraints, supportsGetUserMedia } from '@/lib/audio-utils'

const WORKLET_PATH = '/pcm-processor.js'

export interface UseAudioRecorderOptions {
  onAudioData: (data: Int16Array) => void
  deviceId?: string
  volumeUpdateInterval?: number
}

export interface UseAudioRecorderReturn {
  isRecording: boolean
  error: string | null
  volume: number
  startRecording: () => Promise<void>
  stopRecording: () => void
}

/**
 * Hook for managing audio recording with AudioWorklet
 * Features:
 * - Proper cleanup and resource management
 * - Volume visualization via AnalyserNode
 * - Memory leak prevention
 */
export function useAudioRecorder(options: UseAudioRecorderOptions): UseAudioRecorderReturn {
  const { onAudioData, deviceId, volumeUpdateInterval = 50 } = options

  // Local state
  const [isRecording, setIsRecording] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [volume, setVolume] = useState(0)

  // Store actions
  const { setRecording, setVolume: setStoreVolume, setAudioError } = useAppStore()

  // Audio context hook
  const audioContext = useAudioContext()

  // Refs for audio nodes and cleanup
  const streamRef = useRef<MediaStream | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const volumeIntervalRef = useRef<number | null>(null)
  const isCleaningUpRef = useRef(false)
  const isMountedRef = useRef(true)

  /**
   * Cleanup all audio resources
   */
  const cleanup = useCallback(() => {
    if (isCleaningUpRef.current) return
    isCleaningUpRef.current = true

    console.log('[AudioRecorder] Cleaning up resources...')

    // Stop volume monitoring
    if (volumeIntervalRef.current !== null) {
      clearInterval(volumeIntervalRef.current)
      volumeIntervalRef.current = null
    }

    // Disconnect worklet node
    if (workletNodeRef.current) {
      workletNodeRef.current.port.onmessage = null
      workletNodeRef.current.disconnect()
      workletNodeRef.current = null
    }

    // Disconnect analyser
    if (analyserRef.current) {
      analyserRef.current.disconnect()
      analyserRef.current = null
    }

    // Disconnect source
    if (sourceRef.current) {
      sourceRef.current.disconnect()
      sourceRef.current = null
    }

    // Stop all tracks in the stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        track.stop()
        console.log(`[AudioRecorder] Stopped track: ${track.kind}`)
      })
      streamRef.current = null
    }

    // Close audio context
    audioContext.close()

    // Reset state
    if (isMountedRef.current) {
      setIsRecording(false)
      setRecording(false)
      setVolume(0)
      setStoreVolume(0)
    }

    isCleaningUpRef.current = false
    console.log('[AudioRecorder] Cleanup complete')
  }, [audioContext, setRecording, setStoreVolume])

  /**
   * Start volume monitoring
   */
  const startVolumeMonitoring = useCallback(() => {
    if (!analyserRef.current || volumeIntervalRef.current !== null) return

    const analyser = analyserRef.current
    const dataArray = new Uint8Array(analyser.frequencyBinCount)

    volumeIntervalRef.current = window.setInterval(() => {
      if (!analyserRef.current || !isMountedRef.current) {
        if (volumeIntervalRef.current !== null) {
          clearInterval(volumeIntervalRef.current)
          volumeIntervalRef.current = null
        }
        return
      }

      analyser.getByteFrequencyData(dataArray)

      // Calculate average volume (0-255) and normalize to 0-100
      const sum = dataArray.reduce((a, b) => a + b, 0)
      const avg = (sum / dataArray.length / 255) * 100
      
      setVolume(avg)
      setStoreVolume(avg)
    }, volumeUpdateInterval)
  }, [volumeUpdateInterval, setStoreVolume])

  /**
   * Start recording
   */
  const startRecording = useCallback(async (): Promise<void> => {
    try {
      setError(null)
      setAudioError(null)

      // Check browser support
      if (!supportsGetUserMedia()) {
        throw new Error('getUserMedia is not supported in this browser')
      }

      console.log('[AudioRecorder] Starting recording...')

      // Get microphone stream
      const constraints = getAudioConstraints(deviceId)
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream

      console.log('[AudioRecorder] Got microphone stream', {
        deviceId: deviceId || 'default',
        tracks: stream.getAudioTracks().length,
      })

      // Initialize audio context
      const ctx = await audioContext.initialize()

      // Load AudioWorklet
      await audioContext.loadWorklet(WORKLET_PATH)
      console.log('[AudioRecorder] AudioWorklet loaded')

      // Create audio nodes
      const source = audioContext.createMediaStreamSource(stream)
      sourceRef.current = source

      const analyser = audioContext.createAnalyser(256)
      analyserRef.current = analyser

      const workletNode = audioContext.createWorkletNode('pcm-processor')
      workletNodeRef.current = workletNode

      // Handle data from worklet
      let packetCount = 0
      workletNode.port.onmessage = (event: MessageEvent) => {
        if (!isMountedRef.current) return

        const int16Data = new Int16Array(event.data)
        packetCount++

        // Log every 20th packet for debugging
        if (packetCount % 20 === 0) {
          console.log(`[AudioRecorder] Packet #${packetCount}: ${int16Data.length} samples`)
        }

        onAudioData(int16Data)
      }

      // Connect audio graph: Source -> Analyser -> Worklet -> Destination
      source.connect(analyser)
      analyser.connect(workletNode)
      
      // Connect to destination to keep the audio graph alive
      // (Some browsers require this)
      workletNode.connect(ctx.destination)

      // Start volume monitoring
      startVolumeMonitoring()

      // Update state
      setIsRecording(true)
      setRecording(true)

      console.log('[AudioRecorder] Recording started successfully')

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start recording'
      console.error('[AudioRecorder] Error starting recording:', errorMessage)
      
      setError(errorMessage)
      setAudioError(errorMessage)
      cleanup()
    }
  }, [
    deviceId,
    audioContext,
    onAudioData,
    startVolumeMonitoring,
    cleanup,
    setRecording,
    setAudioError,
  ])

  /**
   * Stop recording
   */
  const stopRecording = useCallback((): void => {
    console.log('[AudioRecorder] Stopping recording...')
    cleanup()
  }, [cleanup])

  // Track mounted state
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup()
    }
  }, [cleanup])

  // Cleanup when deviceId changes while recording
  useEffect(() => {
    if (isRecording && deviceId) {
      console.log('[AudioRecorder] Device changed, restarting recording...')
      stopRecording()
      // Note: Not auto-restarting to let user explicitly restart
    }
  }, [deviceId]) // eslint-disable-line react-hooks/exhaustive-deps

  return {
    isRecording,
    error,
    volume,
    startRecording,
    stopRecording,
  }
}
