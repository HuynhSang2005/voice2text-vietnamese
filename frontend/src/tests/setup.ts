/**
 * Vitest Test Setup
 * Mocks for browser APIs: WebSocket, AudioWorklet, MediaDevices, etc.
 */
import { vi, beforeEach, afterEach } from 'vitest'
import '@testing-library/jest-dom/vitest'

// ==================== WebSocket Mock ====================
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  url: string
  readyState: number = MockWebSocket.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  
  private _protocols: string | string[] | undefined

  constructor(url: string, protocols?: string | string[]) {
    this.url = url
    this._protocols = protocols
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      if (this.onopen) {
        this.onopen(new Event('open'))
      }
    }, 0)
  }

  send = vi.fn((data: string | ArrayBuffer) => {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open')
    }
  })

  close = vi.fn((code?: number, reason?: string) => {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code: code || 1000, reason }))
    }
  })

  // Helper for tests to simulate messages
  simulateMessage(data: string | object) {
    if (this.onmessage) {
      const messageData = typeof data === 'object' ? JSON.stringify(data) : data
      this.onmessage(new MessageEvent('message', { data: messageData }))
    }
  }

  // Helper for tests to simulate errors
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'))
    }
  }

  // Helper for tests to simulate close
  simulateClose(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason }))
    }
  }
}

// @ts-expect-error - Assign mock to global
global.WebSocket = MockWebSocket

// ==================== AudioContext Mock ====================
class MockAudioContext {
  state: AudioContextState = 'running'
  sampleRate = 16000
  destination = {} as AudioDestinationNode
  
  private _worklets: Set<string> = new Set()

  createMediaStreamSource = vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
  }))

  createAnalyser = vi.fn(() => ({
    fftSize: 256,
    frequencyBinCount: 128,
    connect: vi.fn(),
    disconnect: vi.fn(),
    getByteFrequencyData: vi.fn((array: Uint8Array) => {
      // Fill with mock volume data
      for (let i = 0; i < array.length; i++) {
        array[i] = Math.random() * 100 // Random low volume
      }
    }),
  }))

  audioWorklet = {
    addModule: vi.fn(async (url: string) => {
      this._worklets.add(url)
    }),
  }

  resume = vi.fn(async () => {
    this.state = 'running'
  })

  close = vi.fn(async () => {
    this.state = 'closed'
  })
}

// @ts-expect-error - Assign mock to global
global.AudioContext = MockAudioContext
// @ts-expect-error - Webkit prefix
global.webkitAudioContext = MockAudioContext

// ==================== AudioWorkletNode Mock ====================
class MockAudioWorkletNode {
  port = {
    onmessage: null as ((event: MessageEvent) => void) | null,
    postMessage: vi.fn(),
  }

  constructor(context: MockAudioContext, name: string) {}

  connect = vi.fn()
  disconnect = vi.fn()

  // Helper to simulate audio data from worklet
  simulateAudioData(data: Int16Array) {
    if (this.port.onmessage) {
      this.port.onmessage(new MessageEvent('message', { data: data.buffer }))
    }
  }
}

// @ts-expect-error - Assign mock to global
global.AudioWorkletNode = MockAudioWorkletNode

// ==================== MediaDevices Mock ====================
const createMockMediaStream = () => {
  const audioTrack = {
    kind: 'audio' as const,
    id: 'mock-audio-track',
    label: 'Mock Microphone',
    enabled: true,
    stop: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }

  return {
    getTracks: vi.fn(() => [audioTrack]),
    getAudioTracks: vi.fn(() => [audioTrack]),
    getVideoTracks: vi.fn(() => []),
    addTrack: vi.fn(),
    removeTrack: vi.fn(),
    clone: vi.fn(() => createMockMediaStream()),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }
}

const mockMediaDevices = {
  getUserMedia: vi.fn(async () => createMockMediaStream()),
  enumerateDevices: vi.fn(async () => [
    { deviceId: 'default', kind: 'audioinput', label: 'Default Microphone', groupId: 'group1' },
    { deviceId: 'mic-1', kind: 'audioinput', label: 'External Microphone', groupId: 'group2' },
  ]),
  getDisplayMedia: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
}

Object.defineProperty(navigator, 'mediaDevices', {
  value: mockMediaDevices,
  writable: true,
})

// ==================== MessagePort Mock ====================
class MockMessagePort {
  onmessage: ((event: MessageEvent) => void) | null = null
  onmessageerror: ((event: MessageEvent) => void) | null = null
  
  postMessage = vi.fn()
  start = vi.fn()
  close = vi.fn()
  addEventListener = vi.fn()
  removeEventListener = vi.fn()
}

// @ts-expect-error - Assign mock to global
global.MessagePort = MockMessagePort

// ==================== URL Mock ====================
global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
global.URL.revokeObjectURL = vi.fn()

// ==================== Clipboard API Mock ====================
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: vi.fn(async () => {}),
    readText: vi.fn(async () => ''),
  },
  writable: true,
})

// ==================== IntersectionObserver Mock ====================
class MockIntersectionObserver {
  constructor(callback: IntersectionObserverCallback) {}
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
  takeRecords = vi.fn(() => [])
}

// @ts-expect-error - Assign mock to global
global.IntersectionObserver = MockIntersectionObserver

// ==================== ResizeObserver Mock ====================
class MockResizeObserver {
  constructor(callback: ResizeObserverCallback) {}
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

// @ts-expect-error - Assign mock to global
global.ResizeObserver = MockResizeObserver

// ==================== matchMedia Mock ====================
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// ==================== Console Suppress ====================
// Suppress console during tests (can be disabled for debugging)
const originalConsoleError = console.error
const originalConsoleWarn = console.warn

beforeEach(() => {
  // Suppress specific React/testing-library warnings
  console.error = vi.fn((...args) => {
    const message = args[0]?.toString() || ''
    // Filter out known noisy warnings
    if (
      message.includes('Warning: ReactDOM.render') ||
      message.includes('act(...)') ||
      message.includes('inside a test was not wrapped')
    ) {
      return
    }
    originalConsoleError.apply(console, args)
  })
  
  console.warn = vi.fn((...args) => {
    const message = args[0]?.toString() || ''
    if (message.includes('componentWillReceiveProps')) {
      return
    }
    originalConsoleWarn.apply(console, args)
  })
})

afterEach(() => {
  console.error = originalConsoleError
  console.warn = originalConsoleWarn
})

// ==================== Export Mocks for Test Access ====================
export {
  MockWebSocket,
  MockAudioContext,
  MockAudioWorkletNode,
  mockMediaDevices,
  createMockMediaStream,
}
