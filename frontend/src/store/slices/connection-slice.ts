import type { StateCreator } from 'zustand'

export type WebSocketState = 'connecting' | 'open' | 'closing' | 'closed'

export interface ConnectionSlice {
  // State
  wsState: WebSocketState
  lastError: Error | null
  reconnectAttempts: number
  lastConnectedAt: number | null
  
  // Actions
  setWsState: (state: WebSocketState) => void
  setConnectionError: (error: Error | null) => void
  incrementReconnect: () => void
  resetReconnect: () => void
  markConnected: () => void
}

export const createConnectionSlice: StateCreator<
  ConnectionSlice,
  [],
  [],
  ConnectionSlice
> = (set) => ({
  // Initial state
  wsState: 'closed',
  lastError: null,
  reconnectAttempts: 0,
  lastConnectedAt: null,

  // Actions
  setWsState: (wsState) => set({ wsState }),
  
  setConnectionError: (error) => set({ lastError: error }),
  
  incrementReconnect: () => 
    set((state) => ({ reconnectAttempts: state.reconnectAttempts + 1 })),
  
  resetReconnect: () => set({ reconnectAttempts: 0 }),
  
  markConnected: () => set({ 
    lastConnectedAt: Date.now(),
    reconnectAttempts: 0,
    lastError: null 
  }),
})
