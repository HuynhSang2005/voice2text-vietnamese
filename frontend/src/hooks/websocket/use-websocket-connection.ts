import { useCallback, useRef, useEffect } from 'react'
import useWebSocket, { ReadyState } from 'react-use-websocket'
import { useAppStore, type WebSocketState } from '@/store'

// Message queue for storing messages when disconnected
interface QueuedMessage {
  data: string | ArrayBuffer
  timestamp: number
}

export interface WebSocketConnectionConfig {
  url: string
  // Reconnection config
  reconnectAttempts?: number
  maxReconnectInterval?: number
  // Heartbeat config  
  heartbeatInterval?: number
  heartbeatTimeout?: number
  heartbeatMessage?: string
  // Message queue config
  enableMessageQueue?: boolean
  maxQueueSize?: number
  // Callbacks
  onOpen?: () => void
  onClose?: (event: CloseEvent) => void
  onError?: (event: Event) => void
  onMessage?: (event: MessageEvent) => void
  onReconnectStop?: (attempts: number) => void
}

const DEFAULT_CONFIG: Required<Omit<WebSocketConnectionConfig, 'url' | 'onOpen' | 'onClose' | 'onError' | 'onMessage' | 'onReconnectStop'>> = {
  reconnectAttempts: 15,
  maxReconnectInterval: 10000,
  heartbeatInterval: 25000,
  heartbeatTimeout: 60000,
  heartbeatMessage: 'ping',
  enableMessageQueue: true,
  maxQueueSize: 100,
}

// Map ReadyState to our WebSocketState type
const readyStateToWsState = (state: ReadyState): WebSocketState => {
  switch (state) {
    case ReadyState.CONNECTING:
      return 'connecting'
    case ReadyState.OPEN:
      return 'open'
    case ReadyState.CLOSING:
      return 'closing'
    case ReadyState.CLOSED:
    case ReadyState.UNINSTANTIATED:
    default:
      return 'closed'
  }
}

export function useWebSocketConnection(config: WebSocketConnectionConfig) {
  const {
    url,
    reconnectAttempts = DEFAULT_CONFIG.reconnectAttempts,
    maxReconnectInterval = DEFAULT_CONFIG.maxReconnectInterval,
    heartbeatInterval = DEFAULT_CONFIG.heartbeatInterval,
    heartbeatTimeout = DEFAULT_CONFIG.heartbeatTimeout,
    heartbeatMessage = DEFAULT_CONFIG.heartbeatMessage,
    enableMessageQueue = DEFAULT_CONFIG.enableMessageQueue,
    maxQueueSize = DEFAULT_CONFIG.maxQueueSize,
    onOpen,
    onClose,
    onError,
    onMessage,
    onReconnectStop,
  } = config

  // Store actions
  const { 
    setWsState, 
    setConnectionError, 
    incrementReconnect,
    markConnected,
  } = useAppStore()

  // Refs
  const didUnmount = useRef(false)
  const messageQueue = useRef<QueuedMessage[]>([])
  const lastReadyState = useRef<ReadyState>(ReadyState.UNINSTANTIATED)

  // WebSocket hook
  const {
    sendMessage: wsSendMessage,
    lastMessage,
    readyState,
    getWebSocket,
  } = useWebSocket(url, {
    // Reconnection with exponential backoff
    shouldReconnect: (closeEvent) => {
      // Don't reconnect if unmounted or explicit close (1000)
      if (didUnmount.current || closeEvent.code === 1000) {
        return false
      }
      return true
    },
    reconnectAttempts,
    reconnectInterval: (attemptNumber) => {
      // Exponential backoff: 1s, 2s, 4s, 8s... capped at maxReconnectInterval
      const interval = Math.min(Math.pow(2, attemptNumber) * 1000, maxReconnectInterval)
      console.log(`[WS] Reconnect attempt ${attemptNumber + 1}, waiting ${interval}ms`)
      incrementReconnect()
      return interval
    },
    retryOnError: true,
    
    // Heartbeat
    heartbeat: {
      message: heartbeatMessage,
      returnMessage: 'pong',
      timeout: heartbeatTimeout,
      interval: heartbeatInterval,
    },
    
    // Event handlers
    onOpen: () => {
      console.log('[WS] Connection established')
      markConnected()
      
      // Flush queued messages
      if (enableMessageQueue && messageQueue.current.length > 0) {
        console.log(`[WS] Flushing ${messageQueue.current.length} queued messages`)
        const ws = getWebSocket()
        messageQueue.current.forEach(({ data }) => {
          if (ws && 'send' in ws && ws.readyState === WebSocket.OPEN) {
            (ws as WebSocket).send(data)
          }
        })
        messageQueue.current = []
      }
      
      onOpen?.()
    },
    
    onClose: (event) => {
      console.log(`[WS] Connection closed: code=${event.code}, reason=${event.reason}`)
      if (event.code === 4408) {
        console.error('[WS] Connection timed out - no heartbeat response')
      }
      onClose?.(event)
    },
    
    onError: (event) => {
      console.error('[WS] Connection error:', event)
      setConnectionError(new Error('WebSocket connection error'))
      onError?.(event)
    },
    
    onMessage: (event) => {
      // Filter out heartbeat responses
      if (event.data === 'pong') {
        return
      }
      onMessage?.(event)
    },
    
    onReconnectStop: (numAttempts) => {
      console.error(`[WS] Failed to reconnect after ${numAttempts} attempts`)
      setConnectionError(new Error(`Failed to reconnect after ${numAttempts} attempts`))
      onReconnectStop?.(numAttempts)
    },
  })

  // Update store when readyState changes
  useEffect(() => {
    if (readyState !== lastReadyState.current) {
      lastReadyState.current = readyState
      setWsState(readyStateToWsState(readyState))
    }
  }, [readyState, setWsState])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      didUnmount.current = true
    }
  }, [])

  // Enhanced send that queues messages when disconnected
  const sendMessage = useCallback((data: string | ArrayBuffer) => {
    if (readyState === ReadyState.OPEN) {
      wsSendMessage(data)
    } else if (enableMessageQueue) {
      // Queue message if not connected
      if (messageQueue.current.length < maxQueueSize) {
        messageQueue.current.push({
          data,
          timestamp: Date.now(),
        })
        console.log(`[WS] Message queued (queue size: ${messageQueue.current.length})`)
      } else {
        console.warn('[WS] Message queue full, dropping message')
      }
    } else {
      console.warn('[WS] WebSocket not open and queue disabled, dropping message')
    }
  }, [readyState, wsSendMessage, enableMessageQueue, maxQueueSize])

  // Send JSON helper
  const sendJsonMessage = useCallback(<T>(data: T) => {
    sendMessage(JSON.stringify(data))
  }, [sendMessage])

  // Clear message queue
  const clearMessageQueue = useCallback(() => {
    const count = messageQueue.current.length
    messageQueue.current = []
    console.log(`[WS] Cleared ${count} messages from queue`)
  }, [])

  // Get connection info
  const getConnectionInfo = useCallback(() => ({
    readyState,
    isConnected: readyState === ReadyState.OPEN,
    isConnecting: readyState === ReadyState.CONNECTING,
    queuedMessageCount: messageQueue.current.length,
  }), [readyState])

  return {
    // State
    readyState,
    isConnected: readyState === ReadyState.OPEN,
    isConnecting: readyState === ReadyState.CONNECTING,
    lastMessage,
    
    // Actions
    sendMessage,
    sendJsonMessage,
    clearMessageQueue,
    getConnectionInfo,
    getWebSocket,
  }
}

// Re-export ReadyState for convenience
export { ReadyState }
