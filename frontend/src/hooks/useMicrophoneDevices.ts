import { useState, useEffect } from 'react'

export interface MicrophoneDevice {
  deviceId: string
  label: string
}

export function useMicrophoneDevices() {
  const [devices, setDevices] = useState<MicrophoneDevice[]>([])
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('')
  const [hasPermission, setHasPermission] = useState<boolean>(false)

  useEffect(() => {
    const loadDevices = async () => {
      try {
        // Request permission first
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach(track => track.stop())
        setHasPermission(true)

        // Enumerate devices
        const deviceList = await navigator.mediaDevices.enumerateDevices()
        const audioInputs = deviceList
          .filter(device => device.kind === 'audioinput')
          .map(device => ({
            deviceId: device.deviceId,
            label: device.label || `Microphone ${device.deviceId.slice(0, 5)}`
          }))

        setDevices(audioInputs)
        
        // Set default device
        if (audioInputs.length > 0 && !selectedDeviceId) {
          setSelectedDeviceId(audioInputs[0].deviceId)
        }
      } catch (error) {
        console.error('Failed to enumerate devices:', error)
        setHasPermission(false)
      }
    }

    loadDevices()

    // Listen for device changes
    navigator.mediaDevices.addEventListener('devicechange', loadDevices)
    return () => {
      navigator.mediaDevices.removeEventListener('devicechange', loadDevices)
    }
  }, [selectedDeviceId])

  return {
    devices,
    selectedDeviceId,
    setSelectedDeviceId,
    hasPermission
  }
}
