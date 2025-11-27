import { useRef, useCallback, useEffect } from 'react'
import { AUDIO_CONFIG, supportsAudioWorklet } from '@/lib/audio-utils'

export interface UseAudioContextOptions {
  sampleRate?: number
  autoResume?: boolean
}

/**
 * Hook to manage AudioContext lifecycle
 * Handles browser autoplay policies and state management
 */
export function useAudioContext(options: UseAudioContextOptions = {}) {
  const { 
    sampleRate = AUDIO_CONFIG.sampleRate,
    autoResume = true 
  } = options

  const audioContextRef = useRef<AudioContext | null>(null)
  const isInitializedRef = useRef(false)

  /**
   * Initialize AudioContext
   * Must be called from a user gesture (click, etc)
   */
  const initialize = useCallback(async (): Promise<AudioContext> => {
    // Return existing context if already initialized
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      // Resume if suspended
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume()
      }
      return audioContextRef.current
    }

    // Check browser support
    if (!supportsAudioWorklet()) {
      throw new Error('AudioWorklet is not supported in this browser')
    }

    // Create new AudioContext with target sample rate
    const ctx = new AudioContext({ sampleRate })
    audioContextRef.current = ctx
    isInitializedRef.current = true

    console.log(`[AudioContext] Created with sampleRate: ${ctx.sampleRate}`)

    // Handle suspended state (common on mobile)
    if (ctx.state === 'suspended') {
      await ctx.resume()
      console.log('[AudioContext] Resumed from suspended state')
    }

    return ctx
  }, [sampleRate])

  /**
   * Get the current AudioContext (may be null)
   */
  const getContext = useCallback((): AudioContext | null => {
    return audioContextRef.current
  }, [])

  /**
   * Resume suspended AudioContext
   */
  const resume = useCallback(async (): Promise<void> => {
    if (audioContextRef.current?.state === 'suspended') {
      await audioContextRef.current.resume()
      console.log('[AudioContext] Resumed')
    }
  }, [])

  /**
   * Suspend AudioContext (save resources)
   */
  const suspend = useCallback(async (): Promise<void> => {
    if (audioContextRef.current?.state === 'running') {
      await audioContextRef.current.suspend()
      console.log('[AudioContext] Suspended')
    }
  }, [])

  /**
   * Close AudioContext and release resources
   */
  const close = useCallback(async (): Promise<void> => {
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      await audioContextRef.current.close()
      audioContextRef.current = null
      isInitializedRef.current = false
      console.log('[AudioContext] Closed')
    }
  }, [])

  /**
   * Load AudioWorklet processor
   */
  const loadWorklet = useCallback(async (processorPath: string): Promise<void> => {
    const ctx = audioContextRef.current
    if (!ctx) {
      throw new Error('AudioContext not initialized')
    }

    try {
      await ctx.audioWorklet.addModule(processorPath)
      console.log(`[AudioContext] Loaded worklet: ${processorPath}`)
    } catch (error) {
      console.error('[AudioContext] Failed to load worklet:', error)
      throw error
    }
  }, [])

  /**
   * Create MediaStreamSource from microphone stream
   */
  const createMediaStreamSource = useCallback((stream: MediaStream): MediaStreamAudioSourceNode => {
    const ctx = audioContextRef.current
    if (!ctx) {
      throw new Error('AudioContext not initialized')
    }
    return ctx.createMediaStreamSource(stream)
  }, [])

  /**
   * Create AnalyserNode for volume visualization
   */
  const createAnalyser = useCallback((fftSize: number = 256): AnalyserNode => {
    const ctx = audioContextRef.current
    if (!ctx) {
      throw new Error('AudioContext not initialized')
    }
    const analyser = ctx.createAnalyser()
    analyser.fftSize = fftSize
    return analyser
  }, [])

  /**
   * Create AudioWorkletNode
   */
  const createWorkletNode = useCallback((processorName: string): AudioWorkletNode => {
    const ctx = audioContextRef.current
    if (!ctx) {
      throw new Error('AudioContext not initialized')
    }
    return new AudioWorkletNode(ctx, processorName)
  }, [])

  // Auto-resume on user interaction (if enabled)
  useEffect(() => {
    if (!autoResume) return

    const handleUserInteraction = () => {
      if (audioContextRef.current?.state === 'suspended') {
        audioContextRef.current.resume()
      }
    }

    // Listen for user interactions
    document.addEventListener('click', handleUserInteraction, { once: true })
    document.addEventListener('keydown', handleUserInteraction, { once: true })
    document.addEventListener('touchstart', handleUserInteraction, { once: true })

    return () => {
      document.removeEventListener('click', handleUserInteraction)
      document.removeEventListener('keydown', handleUserInteraction)
      document.removeEventListener('touchstart', handleUserInteraction)
    }
  }, [autoResume])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close()
        audioContextRef.current = null
      }
    }
  }, [])

  return {
    // State
    isInitialized: isInitializedRef.current,
    context: audioContextRef.current,
    state: audioContextRef.current?.state ?? null,
    sampleRate: audioContextRef.current?.sampleRate ?? sampleRate,

    // Actions
    initialize,
    getContext,
    resume,
    suspend,
    close,
    loadWorklet,
    createMediaStreamSource,
    createAnalyser,
    createWorkletNode,
  }
}
