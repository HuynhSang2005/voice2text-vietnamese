/**
 * Tests for use-websocket-connection hook
 * Testing: reconnection, heartbeat, message queue, state management
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { ReadyState } from 'react-use-websocket'

// Mock react-use-websocket
const mockSendMessage = vi.fn()
const mockGetWebSocket = vi.fn()
let mockReadyState = ReadyState.OPEN
let mockLastMessage: MessageEvent | null = null
let wsOptions: any = {}

vi.mock('react-use-websocket', () => ({
  __esModule: true,
  default: (url: string, options: any) => {
    wsOptions = options
    return {
      sendMessage: mockSendMessage,
      lastMessage: mockLastMessage,
      readyState: mockReadyState,
      getWebSocket: mockGetWebSocket,
    }
  },
  ReadyState: {
    CONNECTING: 0,
    OPEN: 1,
    CLOSING: 2,
    CLOSED: 3,
    UNINSTANTIATED: -1,
  },
}))

// Mock store
const mockSetWsState = vi.fn()
const mockSetConnectionError = vi.fn()
const mockIncrementReconnect = vi.fn()
const mockMarkConnected = vi.fn()

vi.mock('@/store', () => ({
  useAppStore: () => ({
    setWsState: mockSetWsState,
    setConnectionError: mockSetConnectionError,
    incrementReconnect: mockIncrementReconnect,
    markConnected: mockMarkConnected,
  }),
}))

// Import after mocks
import { useWebSocketConnection, type WebSocketConnectionConfig } from '../use-websocket-connection'

describe('useWebSocketConnection', () => {
  const defaultConfig: WebSocketConnectionConfig = {
    url: 'ws://localhost:8000/ws',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockReadyState = ReadyState.OPEN
    mockLastMessage = null
    wsOptions = {}
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Basic Connection', () => {
    it('should establish connection with provided URL', () => {
      const { result } = renderHook(() => useWebSocketConnection(defaultConfig))

      expect(result.current.isConnected).toBe(true)
      expect(result.current.isConnecting).toBe(false)
      expect(result.current.readyState).toBe(ReadyState.OPEN)
    })

    it('should call markConnected on open', () => {
      renderHook(() => useWebSocketConnection(defaultConfig))

      // Simulate onOpen callback
      act(() => {
        wsOptions.onOpen?.()
      })

      expect(mockMarkConnected).toHaveBeenCalled()
    })

    it('should set connection error on error', () => {
      renderHook(() => useWebSocketConnection(defaultConfig))

      // Simulate error
      act(() => {
        wsOptions.onError?.(new Event('error'))
      })

      expect(mockSetConnectionError).toHaveBeenCalledWith(expect.any(Error))
    })
  })

  describe('Message Sending', () => {
    it('should send message when connected', () => {
      const { result } = renderHook(() => useWebSocketConnection(defaultConfig))

      act(() => {
        result.current.sendMessage('test message')
      })

      expect(mockSendMessage).toHaveBeenCalledWith('test message')
    })

    it('should send JSON message correctly', () => {
      const { result } = renderHook(() => useWebSocketConnection(defaultConfig))

      const testData = { type: 'start_session', sessionId: '123' }

      act(() => {
        result.current.sendJsonMessage(testData)
      })

      expect(mockSendMessage).toHaveBeenCalledWith(JSON.stringify(testData))
    })

    it('should send ArrayBuffer data', () => {
      const { result } = renderHook(() => useWebSocketConnection(defaultConfig))

      const audioData = new Int16Array([1, 2, 3]).buffer

      act(() => {
        result.current.sendMessage(audioData)
      })

      expect(mockSendMessage).toHaveBeenCalledWith(audioData)
    })
  })

  describe('Message Queue', () => {
    it('should queue messages when disconnected', () => {
      mockReadyState = ReadyState.CLOSED

      const { result } = renderHook(() => useWebSocketConnection(defaultConfig))

      // Send message while disconnected
      act(() => {
        result.current.sendMessage('queued message')
      })

      // Should not send directly
      expect(mockSendMessage).not.toHaveBeenCalled()

      // Check queue size
      const info = result.current.getConnectionInfo()
      expect(info.queuedMessageCount).toBe(1)
    })

    it('should flush queue on reconnection', () => {
      mockReadyState = ReadyState.CLOSED

      const mockWs = {
        readyState: WebSocket.OPEN,
        send: vi.fn(),
      }
      mockGetWebSocket.mockReturnValue(mockWs)

      const { result } = renderHook(() => useWebSocketConnection(defaultConfig))

      // Queue messages
      act(() => {
        result.current.sendMessage('message 1')
        result.current.sendMessage('message 2')
      })

      // Simulate reconnection
      mockReadyState = ReadyState.OPEN
      act(() => {
        wsOptions.onOpen?.()
      })

      // Queue should be flushed
      expect(mockWs.send).toHaveBeenCalledWith('message 1')
      expect(mockWs.send).toHaveBeenCalledWith('message 2')
    })

    it('should respect maxQueueSize', () => {
      mockReadyState = ReadyState.CLOSED

      const config: WebSocketConnectionConfig = {
        ...defaultConfig,
        maxQueueSize: 2,
      }

      const { result } = renderHook(() => useWebSocketConnection(config))

      // Fill queue
      act(() => {
        result.current.sendMessage('message 1')
        result.current.sendMessage('message 2')
        result.current.sendMessage('message 3') // Should be dropped
      })

      const info = result.current.getConnectionInfo()
      expect(info.queuedMessageCount).toBe(2)
    })

    it('should clear queue on demand', () => {
      mockReadyState = ReadyState.CLOSED

      const { result } = renderHook(() => useWebSocketConnection(defaultConfig))

      // Queue messages
      act(() => {
        result.current.sendMessage('message 1')
        result.current.sendMessage('message 2')
      })

      // Clear queue
      act(() => {
        result.current.clearMessageQueue()
      })

      const info = result.current.getConnectionInfo()
      expect(info.queuedMessageCount).toBe(0)
    })

    it('should disable queue when enableMessageQueue is false', () => {
      mockReadyState = ReadyState.CLOSED

      const config: WebSocketConnectionConfig = {
        ...defaultConfig,
        enableMessageQueue: false,
      }

      const { result } = renderHook(() => useWebSocketConnection(config))

      // Try to send message while disconnected
      act(() => {
        result.current.sendMessage('dropped message')
      })

      const info = result.current.getConnectionInfo()
      expect(info.queuedMessageCount).toBe(0)
    })
  })

  describe('Reconnection', () => {
    it('should configure reconnect attempts', () => {
      const config: WebSocketConnectionConfig = {
        ...defaultConfig,
        reconnectAttempts: 5,
        maxReconnectInterval: 5000,
      }

      renderHook(() => useWebSocketConnection(config))

      expect(wsOptions.reconnectAttempts).toBe(5)
    })

    it('should use exponential backoff for reconnection', () => {
      const config: WebSocketConnectionConfig = {
        ...defaultConfig,
        maxReconnectInterval: 10000,
      }

      renderHook(() => useWebSocketConnection(config))

      // Test reconnectInterval function
      const interval0 = wsOptions.reconnectInterval(0)
      const interval1 = wsOptions.reconnectInterval(1)
      const interval2 = wsOptions.reconnectInterval(2)
      const interval3 = wsOptions.reconnectInterval(3)

      expect(interval0).toBe(1000) // 2^0 * 1000
      expect(interval1).toBe(2000) // 2^1 * 1000
      expect(interval2).toBe(4000) // 2^2 * 1000
      expect(interval3).toBe(8000) // 2^3 * 1000
    })

    it('should cap reconnect interval at maxReconnectInterval', () => {
      const config: WebSocketConnectionConfig = {
        ...defaultConfig,
        maxReconnectInterval: 5000,
      }

      renderHook(() => useWebSocketConnection(config))

      // High attempt number should be capped
      const interval = wsOptions.reconnectInterval(10) // 2^10 * 1000 = 1024000
      expect(interval).toBe(5000)
    })

    it('should increment reconnect counter', () => {
      renderHook(() => useWebSocketConnection(defaultConfig))

      // Simulate reconnection attempt
      act(() => {
        wsOptions.reconnectInterval(0)
      })

      expect(mockIncrementReconnect).toHaveBeenCalled()
    })

    it('should call onReconnectStop when reconnection fails', () => {
      const onReconnectStop = vi.fn()
      const config: WebSocketConnectionConfig = {
        ...defaultConfig,
        onReconnectStop,
      }

      renderHook(() => useWebSocketConnection(config))

      // Simulate reconnection stop
      act(() => {
        wsOptions.onReconnectStop?.(5)
      })

      expect(onReconnectStop).toHaveBeenCalledWith(5)
      expect(mockSetConnectionError).toHaveBeenCalled()
    })

    it('should not reconnect on clean close (code 1000)', () => {
      renderHook(() => useWebSocketConnection(defaultConfig))

      // Test shouldReconnect
      const shouldReconnect = wsOptions.shouldReconnect({
        code: 1000,
        reason: 'Normal closure',
      })

      expect(shouldReconnect).toBe(false)
    })
  })

  describe('Heartbeat', () => {
    it('should configure heartbeat correctly', () => {
      const config: WebSocketConnectionConfig = {
        ...defaultConfig,
        heartbeatInterval: 30000,
        heartbeatTimeout: 90000,
        heartbeatMessage: 'ping',
      }

      renderHook(() => useWebSocketConnection(config))

      expect(wsOptions.heartbeat).toEqual({
        message: 'ping',
        returnMessage: 'pong',
        timeout: 90000,
        interval: 30000,
      })
    })

    it('should filter out pong messages', () => {
      const onMessage = vi.fn()
      const config: WebSocketConnectionConfig = {
        ...defaultConfig,
        onMessage,
      }

      renderHook(() => useWebSocketConnection(config))

      // Simulate pong message
      act(() => {
        wsOptions.onMessage?.({ data: 'pong' } as MessageEvent)
      })

      expect(onMessage).not.toHaveBeenCalled()
    })

    it('should pass non-pong messages to handler', () => {
      const onMessage = vi.fn()
      const config: WebSocketConnectionConfig = {
        ...defaultConfig,
        onMessage,
      }

      renderHook(() => useWebSocketConnection(config))

      // Simulate real message
      const mockEvent = { data: JSON.stringify({ type: 'transcription' }) } as MessageEvent
      act(() => {
        wsOptions.onMessage?.(mockEvent)
      })

      expect(onMessage).toHaveBeenCalledWith(mockEvent)
    })
  })

  describe('State Management', () => {
    it('should update store state on readyState change', async () => {
      mockReadyState = ReadyState.CONNECTING

      const { rerender } = renderHook(() => useWebSocketConnection(defaultConfig))

      // Initial state
      expect(mockSetWsState).toHaveBeenCalledWith('connecting')

      // Change to open
      mockReadyState = ReadyState.OPEN
      rerender()

      await waitFor(() => {
        expect(mockSetWsState).toHaveBeenCalledWith('open')
      })
    })

    it('should return correct connection info', () => {
      mockReadyState = ReadyState.CONNECTING

      const { result } = renderHook(() => useWebSocketConnection(defaultConfig))

      const info = result.current.getConnectionInfo()

      expect(info).toEqual({
        readyState: ReadyState.CONNECTING,
        isConnected: false,
        isConnecting: true,
        queuedMessageCount: 0,
      })
    })
  })

  describe('Callbacks', () => {
    it('should call onOpen callback', () => {
      const onOpen = vi.fn()
      const config: WebSocketConnectionConfig = {
        ...defaultConfig,
        onOpen,
      }

      renderHook(() => useWebSocketConnection(config))

      act(() => {
        wsOptions.onOpen?.()
      })

      expect(onOpen).toHaveBeenCalled()
    })

    it('should call onClose callback with event', () => {
      const onClose = vi.fn()
      const config: WebSocketConnectionConfig = {
        ...defaultConfig,
        onClose,
      }

      renderHook(() => useWebSocketConnection(config))

      const closeEvent = { code: 1006, reason: 'Connection lost' }
      act(() => {
        wsOptions.onClose?.(closeEvent)
      })

      expect(onClose).toHaveBeenCalledWith(closeEvent)
    })

    it('should call onError callback', () => {
      const onError = vi.fn()
      const config: WebSocketConnectionConfig = {
        ...defaultConfig,
        onError,
      }

      renderHook(() => useWebSocketConnection(config))

      const errorEvent = new Event('error')
      act(() => {
        wsOptions.onError?.(errorEvent)
      })

      expect(onError).toHaveBeenCalledWith(errorEvent)
    })
  })

  describe('Cleanup', () => {
    it('should not reconnect after unmount', () => {
      const { unmount } = renderHook(() => useWebSocketConnection(defaultConfig))

      unmount()

      // After unmount, shouldReconnect should return false
      const shouldReconnect = wsOptions.shouldReconnect({ code: 1006 })
      expect(shouldReconnect).toBe(false)
    })
  })
})
