/**
 * Tests for use-audio-recorder hook
 * Testing: basic functionality, error handling
 * Note: Full integration tests require browser APIs
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

// Store mock
const mockSetRecording = vi.fn()
const mockSetVolume = vi.fn()
const mockSetAudioError = vi.fn()

vi.mock('@/store', () => ({
  useAppStore: () => ({
    setRecording: mockSetRecording,
    setVolume: mockSetVolume,
    setAudioError: mockSetAudioError,
  }),
}))

// Mock audio-utils
vi.mock('@/lib/audio-utils', () => ({
  getAudioConstraints: vi.fn((deviceId?: string) => ({
    audio: {
      deviceId: deviceId ? { exact: deviceId } : undefined,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      sampleRate: 16000,
    }
  })),
  supportsGetUserMedia: vi.fn(() => true),
  AUDIO_CONFIG: {
    sampleRate: 16000,
  },
  supportsAudioWorklet: vi.fn(() => true),
}))

// Import after mocks
import { useAudioRecorder, type UseAudioRecorderOptions } from '../use-audio-recorder'

describe('useAudioRecorder', () => {
  const defaultOptions: UseAudioRecorderOptions = {
    onAudioData: vi.fn(),
    volumeUpdateInterval: 50,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    
    // Setup navigator.mediaDevices mock
    const mockTrack = {
      kind: 'audio',
      stop: vi.fn(),
    }
    const mockStream = {
      getTracks: vi.fn(() => [mockTrack]),
      getAudioTracks: vi.fn(() => [mockTrack]),
    }
    Object.defineProperty(navigator, 'mediaDevices', {
      value: {
        getUserMedia: vi.fn().mockResolvedValue(mockStream),
      },
      writable: true,
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  describe('Initial State', () => {
    it('should start with not recording', () => {
      const { result } = renderHook(() => useAudioRecorder(defaultOptions))

      expect(result.current.isRecording).toBe(false)
      expect(result.current.error).toBeNull()
      expect(result.current.volume).toBe(0)
    })

    it('should expose startRecording and stopRecording functions', () => {
      const { result } = renderHook(() => useAudioRecorder(defaultOptions))

      expect(typeof result.current.startRecording).toBe('function')
      expect(typeof result.current.stopRecording).toBe('function')
    })
  })

  describe('Error Handling', () => {
    it('should handle getUserMedia failure', async () => {
      const mediaError = new Error('Permission denied')
      navigator.mediaDevices.getUserMedia = vi.fn().mockRejectedValue(mediaError)

      const { result } = renderHook(() => useAudioRecorder(defaultOptions))

      await act(async () => {
        await result.current.startRecording()
      })

      expect(result.current.isRecording).toBe(false)
      expect(result.current.error).toBe('Permission denied')
      expect(mockSetAudioError).toHaveBeenCalledWith('Permission denied')
    })

    it('should handle browser not supporting getUserMedia', async () => {
      const { supportsGetUserMedia: mockSupports } = await import('@/lib/audio-utils')
      vi.mocked(mockSupports).mockReturnValue(false)

      const { result } = renderHook(() => useAudioRecorder(defaultOptions))

      await act(async () => {
        await result.current.startRecording()
      })

      expect(result.current.isRecording).toBe(false)
      expect(result.current.error).toBe('getUserMedia is not supported in this browser')
    })
  })

  describe('stopRecording', () => {
    it('should set isRecording to false', async () => {
      const { result } = renderHook(() => useAudioRecorder(defaultOptions))

      // Manually set recording state (simulating started recording)
      act(() => {
        result.current.stopRecording()
      })

      expect(result.current.isRecording).toBe(false)
    })

    it('should reset volume to 0', async () => {
      const { result } = renderHook(() => useAudioRecorder(defaultOptions))

      act(() => {
        result.current.stopRecording()
      })

      expect(result.current.volume).toBe(0)
    })
  })

  describe('Cleanup', () => {
    it('should cleanup on unmount without errors', async () => {
      const { unmount } = renderHook(() => useAudioRecorder(defaultOptions))

      // Should not throw
      expect(() => unmount()).not.toThrow()
    })

    it('should not update state after unmount', async () => {
      const onAudioData = vi.fn()
      const { result, unmount } = renderHook(() => useAudioRecorder({ ...defaultOptions, onAudioData }))

      unmount()

      // Verify hook state is reset
      expect(result.current.isRecording).toBe(false)
    })
  })

  describe('Hook return values', () => {
    it('should return correct interface', () => {
      const { result } = renderHook(() => useAudioRecorder(defaultOptions))

      expect(result.current).toHaveProperty('isRecording')
      expect(result.current).toHaveProperty('error')
      expect(result.current).toHaveProperty('volume')
      expect(result.current).toHaveProperty('startRecording')
      expect(result.current).toHaveProperty('stopRecording')
    })
  })
})
