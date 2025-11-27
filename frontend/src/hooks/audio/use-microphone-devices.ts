import { useState, useEffect, useCallback } from 'react'
import { useAppStore } from '@/store'

export interface MicrophoneDevice {
  deviceId: string
  label: string
  isDefault: boolean
}

export interface UseMicrophoneDevicesReturn {
  devices: MicrophoneDevice[]
  selectedDeviceId: string | null
  hasPermission: boolean
  isLoading: boolean
  error: string | null
  setSelectedDeviceId: (id: string) => void
  refreshDevices: () => Promise<void>
}

/**
 * Hook for managing microphone devices
 * Features:
 * - Automatic permission request
 * - Device change detection
 * - Persisted device selection via store
 */
export function useMicrophoneDevices(): UseMicrophoneDevicesReturn {
  const [devices, setDevices] = useState<MicrophoneDevice[]>([])
  const [hasPermission, setHasPermission] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Use store for persisted device selection
  const deviceId = useAppStore((state) => state.deviceId)
  const setDeviceId = useAppStore((state) => state.setDeviceId)

  /**
   * Load available audio input devices
   */
  const loadDevices = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Request permission first to get device labels
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Stop the stream immediately - we just needed permission
      stream.getTracks().forEach(track => track.stop())
      setHasPermission(true)

      // Enumerate devices
      const deviceList = await navigator.mediaDevices.enumerateDevices()
      const audioInputs = deviceList
        .filter(device => device.kind === 'audioinput')
        .map((device, index) => ({
          deviceId: device.deviceId,
          label: device.label || `Microphone ${index + 1}`,
          isDefault: device.deviceId === 'default' || index === 0,
        }))

      setDevices(audioInputs)
      console.log(`[MicrophoneDevices] Found ${audioInputs.length} devices`)

      // Set default device if none selected
      if (audioInputs.length > 0 && !deviceId) {
        const defaultDevice = audioInputs.find(d => d.isDefault) || audioInputs[0]
        setDeviceId(defaultDevice.deviceId)
        console.log(`[MicrophoneDevices] Selected default: ${defaultDevice.label}`)
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to access microphone'
      console.error('[MicrophoneDevices] Error:', errorMessage)
      setError(errorMessage)
      setHasPermission(false)
    } finally {
      setIsLoading(false)
    }
  }, [deviceId, setDeviceId])

  /**
   * Handle device selection
   */
  const setSelectedDeviceId = useCallback((id: string) => {
    const device = devices.find(d => d.deviceId === id)
    if (device) {
      setDeviceId(id)
      console.log(`[MicrophoneDevices] Selected: ${device.label}`)
    }
  }, [devices, setDeviceId])

  /**
   * Refresh device list
   */
  const refreshDevices = useCallback(async () => {
    await loadDevices()
  }, [loadDevices])

  // Initial load
  useEffect(() => {
    loadDevices()
  }, [loadDevices])

  // Listen for device changes
  useEffect(() => {
    const handleDeviceChange = () => {
      console.log('[MicrophoneDevices] Device change detected')
      loadDevices()
    }

    navigator.mediaDevices.addEventListener('devicechange', handleDeviceChange)
    return () => {
      navigator.mediaDevices.removeEventListener('devicechange', handleDeviceChange)
    }
  }, [loadDevices])

  return {
    devices,
    selectedDeviceId: deviceId,
    hasPermission,
    isLoading,
    error,
    setSelectedDeviceId,
    refreshDevices,
  }
}
