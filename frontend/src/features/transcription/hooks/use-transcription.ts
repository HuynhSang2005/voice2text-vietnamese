/**
 * useTranscription Hook
 * 
 * Combined hook integrating audio recording and WebSocket transcription.
 * Provides a simple API for the UI to control the entire transcription flow.
 */

import { useCallback, useMemo } from 'react'
import { useTranscriptionSocket } from '@/hooks/websocket/use-transcription-socket'
import { useAudioRecorder } from '@/hooks/audio/use-audio-recorder'
import { useMicrophoneDevices } from '@/hooks/audio/use-microphone-devices'
import { useAppStore } from '@/store'
import type { TranscriptLineData } from '../components/transcript-display/transcript-line'
import type { TranscriptLine } from '@/store/slices/transcription-slice'

export interface UseTranscriptionReturn {
  // Connection state
  isConnected: boolean
  isConnecting: boolean
  connectionError: string | null

  // Recording state
  isRecording: boolean
  volume: number
  recordingError: string | null

  // Device management
  devices: Array<{ deviceId: string; label: string }>
  selectedDeviceId: string | null
  selectDevice: (deviceId: string) => void
  refreshDevices: () => Promise<void>

  // Transcription state
  sessionId: string | null
  currentModel: string
  partialText: string
  finalTexts: TranscriptLine[] // Store type
  latency: number

  // Formatted transcript lines (for UI)
  transcriptLines: TranscriptLineData[]

  // Actions
  start: () => Promise<void>
  stop: () => void
  clear: () => void
  setModel: (modelId: string) => void
}

/**
 * Main transcription hook combining all functionality
 */
export function useTranscription(): UseTranscriptionReturn {
  // Get store state
  const {
    isRecording,
    currentModel,
    sessionId,
    partialText,
    finalTexts,
    latency,
    setRecording,
    setModel,
    clearTranscript,
  } = useAppStore()

  // Device management
  const {
    devices,
    selectedDeviceId,
    setSelectedDeviceId,
    refreshDevices,
  } = useMicrophoneDevices()

  // WebSocket transcription
  const {
    isConnected,
    isConnecting,
    sendAudio,
    startSession,
    endSession,
    clear: socketClear,
  } = useTranscriptionSocket()

  // Audio recorder
  const {
    error: recordingError,
    volume,
    startRecording,
    stopRecording,
  } = useAudioRecorder({
    onAudioData: sendAudio,
    deviceId: selectedDeviceId || undefined,
  })

  // Start transcription flow
  const start = useCallback(async () => {
    if (isRecording) return

    try {
      // Generate session ID
      const newSessionId = crypto.randomUUID()
      
      // Start WebSocket session
      startSession(newSessionId)
      
      // Clear previous transcript
      clearTranscript()
      
      // Start audio recording
      await startRecording()
      
      // Update state
      setRecording(true)

      console.log(`[useTranscription] Started session: ${newSessionId}`)
    } catch (error) {
      console.error('[useTranscription] Failed to start:', error)
      setRecording(false)
      throw error
    }
  }, [isRecording, startSession, clearTranscript, startRecording, setRecording])

  // Stop transcription flow
  const stop = useCallback(() => {
    if (!isRecording) return

    console.log('[useTranscription] Stopping...')
    
    // Stop audio recording first
    stopRecording()
    
    // End WebSocket session
    endSession()
    
    // Update state
    setRecording(false)
  }, [isRecording, stopRecording, endSession, setRecording])

  // Clear transcript
  const clear = useCallback(() => {
    clearTranscript()
    socketClear()
  }, [clearTranscript, socketClear])

  // Convert finalTexts to TranscriptLineData format
  const transcriptLines = useMemo<TranscriptLineData[]>(() => {
    return finalTexts.map((line, index) => ({
      id: line.id || `line-${index}`,
      text: line.text,
      timestamp: line.timestamp,
      isFinal: line.isFinal,
      latency: index === finalTexts.length - 1 ? latency : undefined,
    }))
  }, [finalTexts, latency])

  // Select device handler
  const selectDevice = useCallback((deviceId: string) => {
    if (!isRecording) {
      setSelectedDeviceId(deviceId)
    }
  }, [isRecording, setSelectedDeviceId])

  return {
    // Connection state
    isConnected,
    isConnecting,
    connectionError: null, // TODO: Add connection error handling

    // Recording state
    isRecording,
    volume,
    recordingError,

    // Device management
    devices,
    selectedDeviceId,
    selectDevice,
    refreshDevices,

    // Transcription state
    sessionId,
    currentModel,
    partialText,
    finalTexts,
    latency,

    // Formatted lines
    transcriptLines,

    // Actions
    start,
    stop,
    clear,
    setModel,
  }
}

export default useTranscription
