import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

export type ModelId = 'zipformer' | 'faster-whisper' | 'phowhisper' | 'hkab'

interface AppState {
  // Selected model
  selectedModel: ModelId
  setSelectedModel: (model: ModelId) => void

  // Recording state
  isRecording: boolean
  setIsRecording: (isRecording: boolean) => void

  // Current transcription session
  sessionId: string | null
  setSessionId: (sessionId: string | null) => void

  // Current transcript text
  currentTranscript: string
  setCurrentTranscript: (text: string) => void
  appendTranscript: (text: string) => void
  clearTranscript: () => void
}

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
        // Default values
        selectedModel: 'zipformer',
        setSelectedModel: (model) => set({ selectedModel: model }),

        isRecording: false,
        setIsRecording: (isRecording) => set({ isRecording }),

        sessionId: null,
        setSessionId: (sessionId) => set({ sessionId }),

        currentTranscript: '',
        setCurrentTranscript: (text) => set({ currentTranscript: text }),
        appendTranscript: (text) =>
          set((state) => ({
            currentTranscript: state.currentTranscript + text,
          })),
        clearTranscript: () => set({ currentTranscript: '' }),
      }),
      {
        name: 'voice2text-storage',
        partialize: (state) => ({
          selectedModel: state.selectedModel,
        }),
      }
    )
  )
)
