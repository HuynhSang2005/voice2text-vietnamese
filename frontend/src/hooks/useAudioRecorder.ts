import { useState, useRef, useCallback, useEffect } from 'react'

interface UseAudioRecorderProps {
  onAudioData: (data: Int16Array) => void
}

export function useAudioRecorder({ onAudioData }: UseAudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const audioContextRef = useRef<AudioContext | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const startRecording = useCallback(async () => {
    try {
      setError(null)
      
      // 1. Get Microphone Stream
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
          channelCount: 1, 
          echoCancellation: true, 
          autoGainControl: true,
          noiseSuppression: true
        } 
      })
      streamRef.current = stream

      // 2. Create AudioContext (16kHz preferred)
      const ctx = new AudioContext({ sampleRate: 16000 })
      audioContextRef.current = ctx

      // 3. Load AudioWorklet
      await ctx.audioWorklet.addModule('/pcm-processor.js')

      // 4. Create Source & Worklet Node
      const source = ctx.createMediaStreamSource(stream)
      const workletNode = new AudioWorkletNode(ctx, 'pcm-processor')
      
      // 5. Handle Data from Worklet
      workletNode.port.onmessage = (event) => {
        const int16Data = new Int16Array(event.data)
        onAudioData(int16Data)
      }

      // 6. Connect Graph
      source.connect(workletNode)
      workletNode.connect(ctx.destination) // Necessary to keep the processor alive in some browsers
      
      workletNodeRef.current = workletNode
      setIsRecording(true)

    } catch (err) {
      console.error('Failed to start recording:', err)
      setError(err instanceof Error ? err.message : 'Unknown error')
      stopRecording()
    }
  }, [onAudioData])

  const stopRecording = useCallback(() => {
    // 1. Stop Stream Tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }

    // 2. Disconnect Worklet
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect()
      workletNodeRef.current = null
    }

    // 3. Close Context
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    setIsRecording(false)
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isRecording) {
        stopRecording()
      }
    }
  }, [isRecording, stopRecording])

  return {
    isRecording,
    error,
    startRecording,
    stopRecording
  }
}
