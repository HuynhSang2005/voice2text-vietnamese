import { useState, useRef, useCallback, useEffect } from 'react'

interface UseAudioRecorderProps {
  onAudioData: (data: Int16Array) => void
  deviceId?: string
}

export function useAudioRecorder({ onAudioData, deviceId }: UseAudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [volume, setVolume] = useState(0)
  
  const audioContextRef = useRef<AudioContext | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)

  const updateVolume = useCallback(() => {
    if (analyserRef.current && isRecording) {
      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
      analyserRef.current.getByteFrequencyData(dataArray)
      
      // Calculate average volume
      const sum = dataArray.reduce((a, b) => a + b, 0)
      const avg = sum / dataArray.length
      setVolume(avg) // 0-255 roughly
      
      animationFrameRef.current = requestAnimationFrame(updateVolume)
    }
  }, [isRecording])

  const startRecording = useCallback(async () => {
    try {
      setError(null)
      console.log("Starting recording...")
      
      // 1. Get Microphone Stream
      const constraints: MediaStreamConstraints = {
        audio: deviceId 
          ? { 
              deviceId: { exact: deviceId },
              channelCount: 1, 
              echoCancellation: true, 
              autoGainControl: true,
              noiseSuppression: true
            }
          : { 
              channelCount: 1, 
              echoCancellation: true, 
              autoGainControl: true,
              noiseSuppression: true
            }
      }
      
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream
      console.log("Microphone stream acquired", deviceId ? `(Device: ${deviceId})` : "(Default device)")

      // 2. Create AudioContext (16kHz preferred)
      const ctx = new AudioContext({ sampleRate: 16000 })
      audioContextRef.current = ctx

      // 3. Load AudioWorklet
      try {
        await ctx.audioWorklet.addModule('/pcm-processor.js')
        console.log("AudioWorklet loaded")
      } catch (e) {
        console.error("Failed to load AudioWorklet:", e)
        throw new Error("Failed to load audio processor. Check console.")
      }

      // 4. Create Nodes
      const source = ctx.createMediaStreamSource(stream)
      const workletNode = new AudioWorkletNode(ctx, 'pcm-processor')
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      analyserRef.current = analyser
      
      // 5. Handle Data from Worklet
      let packetCount = 0
      workletNode.port.onmessage = (event) => {
        const int16Data = new Int16Array(event.data)
        packetCount++
        if (packetCount % 20 === 0) {
            console.log(`[useAudioRecorder] Received ${int16Data.length} samples from worklet (Packet #${packetCount})`)
        }
        onAudioData(int16Data)
      }

      // 6. Connect Graph
      // Source -> Analyser -> Worklet -> Destination
      // Note: Worklet usually doesn't need to go to destination if we just want data, 
      // but some browsers require it to keep running. 
      // We don't want to hear ourselves, so maybe just Source -> Worklet -> Destination (muted?)
      // Or Source -> Analyser -> Worklet.
      
      source.connect(analyser)
      analyser.connect(workletNode)
      workletNode.connect(ctx.destination) 
      
      workletNodeRef.current = workletNode
      setIsRecording(true)
      
      // Start volume visualization
      updateVolume()

    } catch (err) {
      console.error('Failed to start recording:', err)
      setError(err instanceof Error ? err.message : 'Unknown error')
      stopRecording()
    }
  }, [onAudioData, updateVolume, deviceId])

  const stopRecording = useCallback(() => {
    console.log("Stopping recording...")
    
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }

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
    setVolume(0)
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isRecording) {
        stopRecording()
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [isRecording, stopRecording])

  useEffect(() => {
    if (isRecording) {
        updateVolume()
    }
  }, [isRecording, updateVolume])

  return {
    isRecording,
    error,
    volume,
    startRecording,
    stopRecording
  }
}
