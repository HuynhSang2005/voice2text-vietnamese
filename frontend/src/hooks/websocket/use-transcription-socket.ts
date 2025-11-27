import { useCallback, useEffect, useRef } from 'react'
import { useWebSocketConnection, ReadyState } from './use-websocket-connection'
import { useAppStore } from '@/store'
import { WS_URL } from '@/lib/constants'

// Message types for WebSocket communication
interface TranscriptionMessage {
  type: 'transcription'
  text: string
  is_final: boolean
  latency?: number
}

interface ErrorMessage {
  type: 'error'
  code: string
  message: string
}

interface ModelLoadedMessage {
  type: 'model_loaded'
  model: string
}

type ServerMessage = TranscriptionMessage | ErrorMessage | ModelLoadedMessage | { type: string }

// Client message types
interface ConfigMessage {
  type: 'config'
  model: string
}

interface StartSessionMessage {
  type: 'start_session'
  sessionId: string
}

interface EndSessionMessage {
  type: 'end_session'
}

export function useTranscriptionSocket() {
  const {
    currentModel,
    sessionId,
    setPartialText,
    addFinalText,
    setLatency,
    startSession: storeStartSession,
    endSession: storeEndSession,
  } = useAppStore()

  // Track if config has been sent
  const configSentRef = useRef(false)
  const currentModelRef = useRef(currentModel)

  // Update ref when model changes
  useEffect(() => {
    currentModelRef.current = currentModel
  }, [currentModel])

  // WebSocket connection
  const {
    isConnected,
    isConnecting,
    lastMessage,
    sendMessage,
    sendJsonMessage,
    readyState,
  } = useWebSocketConnection({
    url: WS_URL,
    onOpen: () => {
      // Send config immediately on connect
      console.log('[TranscriptionSocket] Connected, sending config')
      sendJsonMessage<ConfigMessage>({ 
        type: 'config', 
        model: currentModelRef.current 
      })
      configSentRef.current = true
    },
    onClose: () => {
      configSentRef.current = false
    },
  })

  // Handle incoming messages
  useEffect(() => {
    if (!lastMessage) return

    try {
      const data = JSON.parse(lastMessage.data) as ServerMessage

      switch (data.type) {
        case 'transcription': {
          const msg = data as TranscriptionMessage
          if (msg.is_final) {
            if (msg.text.trim()) {
              addFinalText(msg.text)
            }
          } else {
            setPartialText(msg.text)
          }
          if (msg.latency !== undefined) {
            setLatency(msg.latency)
          }
          break
        }

        case 'error': {
          const errMsg = data as ErrorMessage
          console.error(`[TranscriptionSocket] Server error: ${errMsg.code} - ${errMsg.message}`)
          break
        }

        case 'model_loaded': {
          const modelMsg = data as ModelLoadedMessage
          console.log(`[TranscriptionSocket] Model loaded: ${modelMsg.model}`)
          break
        }

        default:
          // Unknown message type - log but don't crash
          if (data.type !== 'pong') {
            console.log('[TranscriptionSocket] Unknown message type:', data.type)
          }
      }
    } catch (e) {
      console.error('[TranscriptionSocket] Failed to parse message:', e)
    }
  }, [lastMessage, setPartialText, addFinalText, setLatency])

  // Handle model change - re-send config if connected
  useEffect(() => {
    if (isConnected && configSentRef.current && currentModel !== currentModelRef.current) {
      console.log(`[TranscriptionSocket] Switching model to: ${currentModel}`)
      sendJsonMessage<ConfigMessage>({ type: 'config', model: currentModel })
      currentModelRef.current = currentModel
    }
  }, [currentModel, isConnected, sendJsonMessage])

  // Send audio data
  const sendAudio = useCallback((audioData: Int16Array) => {
    if (readyState === ReadyState.OPEN) {
      // Create a copy of the buffer as ArrayBuffer to ensure type safety
      const buffer = audioData.buffer.slice(
        audioData.byteOffset,
        audioData.byteOffset + audioData.byteLength
      ) as ArrayBuffer
      sendMessage(buffer)
    }
    // Note: If not connected, the WebSocket hook will queue the message
  }, [readyState, sendMessage])

  // Start a new transcription session
  const startSession = useCallback((sessionId: string) => {
    console.log(`[TranscriptionSocket] Starting session: ${sessionId}`)
    storeStartSession(sessionId)
    
    if (isConnected) {
      sendJsonMessage<StartSessionMessage>({ 
        type: 'start_session', 
        sessionId 
      })
    }
  }, [isConnected, sendJsonMessage, storeStartSession])

  // End current transcription session
  const endSession = useCallback(() => {
    console.log('[TranscriptionSocket] Ending session')
    storeEndSession()
    
    if (isConnected) {
      sendJsonMessage<EndSessionMessage>({ type: 'end_session' })
    }
  }, [isConnected, sendJsonMessage, storeEndSession])

  // Clear transcript
  const clear = useCallback(() => {
    useAppStore.getState().clearTranscript()
  }, [])

  return {
    // Connection state
    isConnected,
    isConnecting,
    readyState,
    
    // Transcription state (from store)
    sessionId,
    partialText: useAppStore.getState().partialText,
    finalTexts: useAppStore.getState().finalTexts,
    latency: useAppStore.getState().latency,
    
    // Actions
    sendAudio,
    startSession,
    endSession,
    clear,
  }
}

// Re-export for backward compatibility
export { ReadyState }
