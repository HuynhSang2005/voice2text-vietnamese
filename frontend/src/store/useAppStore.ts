import { create } from 'zustand'
import { 
  createConnectionSlice, 
  createRecordingSlice, 
  createTranscriptionSlice,
  type ConnectionSlice,
  type RecordingSlice,
  type TranscriptionSlice,
} from './slices'

// Combined store type
export type AppStore = ConnectionSlice & RecordingSlice & TranscriptionSlice

// Backward compatibility selectors
interface LegacySelectors {
  // Legacy state mappings
  isConnected: boolean
  finalText: string[]
  
  // Legacy actions
  setConnected: (status: boolean) => void
}

export const useAppStore = create<AppStore & LegacySelectors>()((...args) => {
  const [set, get] = args
  
  const connectionSlice = createConnectionSlice(...args)
  const recordingSlice = createRecordingSlice(...args)
  const transcriptionSlice = createTranscriptionSlice(...args)
  
  return {
    // Spread all slices
    ...connectionSlice,
    ...recordingSlice,
    ...transcriptionSlice,
    
    // Backward compatibility: isConnected derived from wsState
    get isConnected() {
      return get().wsState === 'open'
    },
    
    // Backward compatibility: finalText as string array
    get finalText() {
      return get().finalTexts.map(t => t.text)
    },
    
    // Backward compatibility: setConnected maps to setWsState
    setConnected: (status: boolean) => {
      set({ wsState: status ? 'open' : 'closed' })
    },
  }
})

// Typed selector hooks for better performance
export const useConnectionState = () => useAppStore((state) => ({
  wsState: state.wsState,
  isConnected: state.wsState === 'open',
  lastError: state.lastError,
  reconnectAttempts: state.reconnectAttempts,
}))

export const useRecordingState = () => useAppStore((state) => ({
  isRecording: state.isRecording,
  volume: state.volume,
  deviceId: state.deviceId,
  audioError: state.audioError,
}))

export const useTranscriptionState = () => useAppStore((state) => ({
  currentModel: state.currentModel,
  sessionId: state.sessionId,
  partialText: state.partialText,
  finalTexts: state.finalTexts,
  latency: state.latency,
}))

