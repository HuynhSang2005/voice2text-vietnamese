import { renderHook, act } from '@testing-library/react'
import { useTranscribe } from '../useTranscribe'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ReadyState } from 'react-use-websocket'

// Mock react-use-websocket
const mockSendMessage = vi.fn()
const mockUseWebSocket = vi.fn()

vi.mock('react-use-websocket', () => ({
  __esModule: true,
  default: (url: string, options: any) => {
      mockUseWebSocket(url, options)
      return {
          sendMessage: mockSendMessage,
          lastMessage: null,
          readyState: ReadyState.OPEN,
      }
  },
  ReadyState: {
      OPEN: 1,
      CLOSED: 3
  }
}))

// Mock store
const mockSetConnected = vi.fn()
const mockSetPartialText = vi.fn()

vi.mock('@/store/useAppStore', () => ({
  useAppStore: () => ({
    currentModel: 'zipformer',
    setConnected: mockSetConnected,
    setPartialText: mockSetPartialText,
    addFinalText: vi.fn(),
    setLatency: vi.fn()
  })
}))

describe('useTranscribe', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should send start_session message correctly', () => {
    const { result } = renderHook(() => useTranscribe())
    
    const sessionId = 'test-session-123'
    
    act(() => {
      result.current.startSession(sessionId)
    })
    
    expect(mockSendMessage).toHaveBeenCalledWith(JSON.stringify({
      type: 'start_session',
      sessionId: sessionId
    }))
    
    // Should verify it clears partial text
    expect(mockSetPartialText).toHaveBeenCalledWith('')
  })

  it('should send audio data when connected', () => {
    const { result } = renderHook(() => useTranscribe())
    
    const dummyAudio = new Int16Array([1, 2, 3])
    
    act(() => {
      result.current.sendAudio(dummyAudio)
    })
    
    expect(mockSendMessage).toHaveBeenCalledWith(dummyAudio)
  })
})
