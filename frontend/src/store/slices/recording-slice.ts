import type { StateCreator } from 'zustand'

export interface RecordingSlice {
  // State
  isRecording: boolean
  volume: number
  deviceId: string | null
  audioError: string | null
  
  // Actions
  setRecording: (status: boolean) => void
  setVolume: (vol: number) => void
  setDeviceId: (id: string | null) => void
  setAudioError: (error: string | null) => void
  resetRecording: () => void
}

export const createRecordingSlice: StateCreator<
  RecordingSlice,
  [],
  [],
  RecordingSlice
> = (set) => ({
  // Initial state
  isRecording: false,
  volume: 0,
  deviceId: null,
  audioError: null,

  // Actions
  setRecording: (isRecording) => set({ isRecording }),
  
  setVolume: (volume) => set({ volume }),
  
  setDeviceId: (deviceId) => set({ deviceId }),
  
  setAudioError: (audioError) => set({ audioError }),
  
  resetRecording: () => set({
    isRecording: false,
    volume: 0,
    audioError: null,
  }),
})
