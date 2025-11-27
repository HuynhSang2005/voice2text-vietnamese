import useWebSocket, { ReadyState } from 'react-use-websocket'
import { useAppStore } from '@/store/useAppStore'
import { useEffect, useCallback } from 'react'

import { WS_URL } from '@/lib/constants'

export const useTranscribe = () => {

  const {
    currentModel,
    setConnected,
    setPartialText,
    addFinalText,
    setLatency
  } = useAppStore()

  // Use constant from env/config


  const { sendMessage, lastMessage, readyState } = useWebSocket(WS_URL, {
    onOpen: () => {
      console.log('WebSocket Connected')
      setConnected(true)
      // Send config immediately on connect
      sendMessage(JSON.stringify({ type: 'config', model: currentModel }))
    },
    onClose: () => {
      console.log('WebSocket Disconnected')
      setConnected(false)
    },
    onError: (event) => {
      console.error('WebSocket Error', event)
      setConnected(false)
    },
    shouldReconnect: () => true, // Auto-reconnect
    reconnectInterval: 3000,
  })

  // Handle incoming messages
  useEffect(() => {
    if (lastMessage !== null) {
      try {
        const data = JSON.parse(lastMessage.data)
        // Expected format: { text: string, is_final: boolean, latency?: number }
        
        if (data.is_final) {
          addFinalText(data.text)
          setPartialText('')
        } else {
          setPartialText(data.text)
        }
        
        if (data.latency) {
            setLatency(data.latency)
        }
      } catch (e) {
        console.error("Failed to parse WS message", e)
      }
    }
  }, [lastMessage, setPartialText, addFinalText, setLatency])

  // Handle model change - re-send config if connected
  useEffect(() => {
      if (readyState === ReadyState.OPEN) {
           console.log(`Switching model to: ${currentModel}`)
           sendMessage(JSON.stringify({ type: 'config', model: currentModel }))
      }
  }, [currentModel, readyState, sendMessage])

  const sendAudio = useCallback((audioData: Int16Array) => {
    if (readyState === ReadyState.OPEN) {
      // console.log(`[useTranscribe] Sending ${audioData.byteLength} bytes`)
      sendMessage(audioData)
    } else {
        console.warn('[useTranscribe] WebSocket not OPEN. Dropping audio.')
    }
  }, [readyState, sendMessage])

  const startSession = useCallback((sessionId: string) => {
      if (readyState === ReadyState.OPEN) {
          console.log(`[useTranscribe] Starting session: ${sessionId}`)
          sendMessage(JSON.stringify({ type: 'start_session', sessionId }))
          // Clear partial text on new session
          setPartialText('')
      }
  }, [readyState, sendMessage, setPartialText])

  return {
    readyState,
    sendAudio,
    startSession
  }
}
