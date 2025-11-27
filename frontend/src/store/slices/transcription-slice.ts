import type { StateCreator } from 'zustand'

export type ModelId = 'zipformer' | 'faster-whisper' | 'phowhisper' | string

export interface TranscriptLine {
  id: string
  text: string
  timestamp: number
  isFinal: boolean
}

export interface TranscriptionSlice {
  // State
  currentModel: ModelId
  sessionId: string | null
  partialText: string
  finalTexts: TranscriptLine[]
  latency: number
  
  // Actions
  setModel: (model: ModelId) => void
  startSession: (sessionId: string) => void
  endSession: () => void
  setPartialText: (text: string) => void
  addFinalText: (text: string) => void
  clearTranscript: () => void
  setLatency: (ms: number) => void
}

export const createTranscriptionSlice: StateCreator<
  TranscriptionSlice,
  [],
  [],
  TranscriptionSlice
> = (set) => ({
  // Initial state
  currentModel: 'zipformer',
  sessionId: null,
  partialText: '',
  finalTexts: [],
  latency: 0,

  // Actions
  setModel: (currentModel) => set({ currentModel }),
  
  startSession: (sessionId) => set({ 
    sessionId,
    partialText: '',
    // Keep finalTexts for now, user can clear manually
  }),
  
  endSession: () => set({ sessionId: null }),
  
  setPartialText: (partialText) => set({ partialText }),
  
  addFinalText: (text) => {
    const newLine: TranscriptLine = {
      id: crypto.randomUUID(),
      text,
      timestamp: Date.now(),
      isFinal: true,
    }
    set((state) => ({
      finalTexts: [...state.finalTexts, newLine],
      partialText: '', // Clear partial when final arrives
    }))
  },
  
  clearTranscript: () => set({ 
    finalTexts: [], 
    partialText: '' 
  }),
  
  setLatency: (latency) => set({ latency }),
})
