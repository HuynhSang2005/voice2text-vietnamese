import { render, screen, fireEvent } from '@testing-library/react'
import Dashboard from '../Dashboard'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock hooks
const mockStartSession = vi.fn()
const mockStartRecording = vi.fn()
const mockStopRecording = vi.fn()
const mockClearTranscript = vi.fn()

vi.mock('@/hooks/useTranscribe', () => ({
  useTranscribe: () => ({
    sendAudio: vi.fn(),
    startSession: mockStartSession,
    readyState: 1 // OPEN
  })
}))

vi.mock('@/hooks/useAudioRecorder', () => ({
  useAudioRecorder: () => ({
    startRecording: mockStartRecording,
    stopRecording: mockStopRecording,
    volume: 0
  })
}))

vi.mock('@/hooks/useMicrophoneDevices', () => ({
  useMicrophoneDevices: () => ({
    devices: [{ deviceId: 'default', label: 'Default Mic' }],
    selectedDeviceId: 'default',
    setSelectedDeviceId: vi.fn(),
    hasPermission: true
  })
}))

// Mock store
vi.mock('@/store/useAppStore', () => ({
  useAppStore: () => ({
    isConnected: true,
    isRecording: false,
    currentModel: 'zipformer',
    partialText: '',
    finalText: [],
    latency: 0,
    setRecording: vi.fn(),
    setModel: vi.fn(),
    clearTranscript: mockClearTranscript
  })
}))

// Mock react-query
vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({
    data: [{ id: 'zipformer', name: 'Zipformer' }],
    isLoading: false
  }),
  queryOptions: vi.fn()
}))

// Mock crypto.randomUUID
Object.defineProperty(global, 'crypto', {
  value: {
    randomUUID: () => 'mock-uuid-123'
  }
})

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render correctly', () => {
    render(<Dashboard />)
    expect(screen.getByText('Live Transcription')).toBeDefined()
    expect(screen.getByText('Model')).toBeDefined()
  })

  it('should start recording and session on mic click', async () => {
    render(<Dashboard />)
    
    const micButton = screen.getByRole('button') // The big mic button
    fireEvent.click(micButton)
    
    // Verify startSession called with UUID
    expect(mockStartSession).toHaveBeenCalledWith('mock-uuid-123')
    
    // Verify clearTranscript called
    expect(mockClearTranscript).toHaveBeenCalled()
    
    // Verify startRecording called
    expect(mockStartRecording).toHaveBeenCalled()
  })
})
