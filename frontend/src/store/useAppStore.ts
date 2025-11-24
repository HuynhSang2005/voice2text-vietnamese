import { create } from 'zustand'

interface AppState {
  isConnected: boolean
  isRecording: boolean
  currentModel: string
  partialText: string
  finalText: string[]
  latency: number
  
  setConnected: (status: boolean) => void
  setRecording: (status: boolean) => void
  setModel: (model: string) => void
  setPartialText: (text: string) => void
  addFinalText: (text: string) => void
  clearTranscript: () => void
  setLatency: (ms: number) => void
}

export const useAppStore = create<AppState>((set) => ({
  isConnected: false,
  isRecording: false,
  currentModel: 'zipformer', // Default model
  partialText: '',
  finalText: [],
  latency: 0,

  setConnected: (status) => set({ isConnected: status }),
  setRecording: (status) => set({ isRecording: status }),
  setModel: (model) => set({ currentModel: model }),
  setPartialText: (text) => set({ partialText: text }),
  addFinalText: (text) => set((state) => ({ finalText: [...state.finalText, text] })),
  clearTranscript: () => set({ finalText: [], partialText: '' }),
  setLatency: (ms) => set({ latency: ms }),
}))
