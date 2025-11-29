import { useCallback, useEffect, useRef, useState } from 'react'
import useWebSocket, { ReadyState } from 'react-use-websocket'
import type { ModelId } from '@/stores/app.store'

// WebSocket config message
interface ConfigMessage {
  type: 'config'
  model: string
  sample_rate: number
}

// WebSocket start session message - to sync sessionId with BE
interface StartSessionMessage {
  type: 'start_session'
  sessionId: string
}

// WebSocket flush message - to force transcribe remaining audio buffer
interface FlushMessage {
  type: 'flush'
}

// WebSocket transcription response
export interface TranscriptionResponse {
  text: string
  is_final: boolean
  model: string
  session_id?: string
  latency_ms?: number
}

export interface TranscriptionState {
  /** Current interim text (not finalized) */
  interimText: string
  /** All finalized text segments */
  finalizedSegments: string[]
  /** Full transcript (interim + finalized) */
  fullTranscript: string
  /** Current session ID */
  sessionId: string | null
  /** WebSocket connection state */
  connectionState: ReadyState
  /** Last error message */
  error: string | null
}

export interface UseTranscriptionOptions {
  /** Model to use for transcription */
  model: ModelId
  /** Called when new transcription is received */
  onTranscription?: (response: TranscriptionResponse) => void
  /** Called when connection state changes */
  onConnectionChange?: (state: ReadyState) => void
  /** Called on error */
  onError?: (error: string) => void
  /** WebSocket URL (default: ws://localhost:8000/ws/transcribe) */
  wsUrl?: string
  /** Sample rate for audio (default: 16000) */
  sampleRate?: number
}

const WS_URL = 'ws://localhost:8000/ws/transcribe'

/**
 * Custom hook for WebSocket-based transcription
 * Manages connection, sends audio data, and receives transcription results
 * 
 * @example
 * ```tsx
 * const { sendAudio, connect, disconnect, state } = useTranscription({
 *   model: 'zipformer',
 *   onTranscription: (response) => console.log(response.text),
 * })
 * ```
 */
export function useTranscription(options: UseTranscriptionOptions) {
  const {
    model,
    onTranscription,
    onConnectionChange,
    onError,
    wsUrl = WS_URL,
    sampleRate = 16000,
  } = options

  const [state, setState] = useState<TranscriptionState>({
    interimText: '',
    finalizedSegments: [],
    fullTranscript: '',
    sessionId: null,
    connectionState: ReadyState.CLOSED,
    error: null,
  })

  // Track if config has been sent
  const configSentRef = useRef(false)
  // Track if we should connect - USE STATE to trigger re-render
  const [shouldConnect, setShouldConnect] = useState(false)

  // Generate session ID - simple format: timestamp + random string
  const generateSessionId = useCallback(() => {
    const timestamp = Date.now()
    const random = Math.random().toString(36).substring(2, 8)
    return `${timestamp}_${random}`
  }, [])

  // WebSocket connection
  const {
    sendJsonMessage,
    lastMessage,
    readyState,
    getWebSocket,
  } = useWebSocket(
    shouldConnect ? wsUrl : null,
    {
      onOpen: () => {
        console.log('[WS] Connected to transcription server')
        configSentRef.current = false
        // Reset state for new session
        setState((prev) => ({
          ...prev,
          interimText: '',
          finalizedSegments: [],
          fullTranscript: '',
          sessionId: null,
          error: null,
        }))
      },
      onClose: () => {
        console.log('[WS] Disconnected from transcription server')
        configSentRef.current = false
      },
      onError: (event) => {
        console.error('[WS] WebSocket error:', event)
        const errorMsg = 'WebSocket connection error'
        setState((prev) => ({ ...prev, error: errorMsg }))
        onError?.(errorMsg)
      },
      shouldReconnect: (closeEvent) => {
        // Reconnect on unexpected close
        return closeEvent.code !== 1000 && shouldConnect
      },
      reconnectAttempts: 5,
      reconnectInterval: 3000,
    },
    shouldConnect
  )

  // Update connection state
  useEffect(() => {
    setState((prev) => ({ ...prev, connectionState: readyState }))
    onConnectionChange?.(readyState)
  }, [readyState, onConnectionChange])

  // Send config when connected
  useEffect(() => {
    if (readyState === ReadyState.OPEN && !configSentRef.current) {
      const sessionId = generateSessionId()
      const config: ConfigMessage = {
        type: 'config',
        model,
        sample_rate: sampleRate,
      }
      
      sendJsonMessage(config)
      
      // Send start_session to sync sessionId with BE
      const startSession: StartSessionMessage = {
        type: 'start_session',
        sessionId,
      }
      sendJsonMessage(startSession)
      
      configSentRef.current = true
      
      setState((prev) => ({
        ...prev,
        sessionId,
        error: null,
        interimText: '',
        finalizedSegments: [],
        fullTranscript: '',
      }))
      
      console.log('[WS] Config sent:', config, 'Session:', sessionId)
    }
  }, [readyState, model, sampleRate, sendJsonMessage, generateSessionId])

  // Handle incoming messages
  useEffect(() => {
    if (lastMessage === null) return

    try {
      const response: TranscriptionResponse = JSON.parse(lastMessage.data)
      
      setState((prev) => {
        let newInterim = prev.interimText
        let newSegments = [...prev.finalizedSegments]

        if (response.is_final) {
          // Add to finalized segments
          if (response.text.trim()) {
            newSegments.push(response.text.trim())
          }
          newInterim = ''
        } else {
          // Update interim text
          newInterim = response.text
        }

        // Build full transcript
        const fullTranscript = [...newSegments, newInterim]
          .filter(Boolean)
          .join(' ')

        return {
          ...prev,
          interimText: newInterim,
          finalizedSegments: newSegments,
          fullTranscript,
        }
      })

      onTranscription?.(response)
    } catch (error) {
      console.error('[WS] Failed to parse message:', error)
    }
  }, [lastMessage, onTranscription])

  /**
   * Connect to WebSocket server
   */
  const connect = useCallback(() => {
    setShouldConnect(true)
  }, [])

  /**
   * Disconnect from WebSocket server
   */
  const disconnect = useCallback(() => {
    setShouldConnect(false)
    configSentRef.current = false
    
    const ws = getWebSocket()
    if (ws) {
      ws.close(1000, 'User disconnected')
    }
  }, [getWebSocket])

  /**
   * Send flush signal to force transcribe remaining audio buffer
   * Used before disconnecting to ensure all audio is processed
   */
  const flush = useCallback(() => {
    if (readyState !== ReadyState.OPEN) {
      console.warn('[WS] Cannot flush: WebSocket not connected')
      return false
    }
    
    const flushMsg: FlushMessage = { type: 'flush' }
    sendJsonMessage(flushMsg)
    console.log('[WS] Flush signal sent')
    return true
  }, [readyState, sendJsonMessage])

  /**
   * Send audio data (binary) over WebSocket
   * @param audioBuffer - PCM Int16 audio data as ArrayBuffer
   */
  const sendAudio = useCallback((audioBuffer: ArrayBuffer) => {
    if (readyState !== ReadyState.OPEN) {
      console.warn('[WS] Cannot send audio: WebSocket not connected')
      return false
    }

    const ws = getWebSocket()
    if (ws && 'send' in ws && ws.readyState === WebSocket.OPEN) {
      (ws as WebSocket).send(audioBuffer)
      return true
    }
    return false
  }, [readyState, getWebSocket])

  /**
   * Clear current transcription state
   */
  const clearTranscription = useCallback(() => {
    setState((prev) => ({
      ...prev,
      interimText: '',
      finalizedSegments: [],
      fullTranscript: '',
    }))
  }, [])

  /**
   * Check if WebSocket is ready to send data
   */
  const isReady = readyState === ReadyState.OPEN && configSentRef.current

  return {
    // State
    ...state,
    isReady,
    isConnected: readyState === ReadyState.OPEN,
    isConnecting: readyState === ReadyState.CONNECTING,

    // Actions
    connect,
    disconnect,
    sendAudio,
    flush,
    clearTranscription,

    // Connection info
    readyState,
    ReadyState,
  }
}
