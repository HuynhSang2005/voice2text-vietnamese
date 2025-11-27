/**
 * Device Selector Component
 * 
 * Microphone device dropdown with device refresh capability.
 */

import { useEffect, useState } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { RefreshCw, Mic } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

export interface AudioDevice {
  deviceId: string
  label: string
  groupId?: string
}

interface DeviceSelectorProps {
  devices: AudioDevice[]
  selectedDeviceId: string | null
  onDeviceChange: (deviceId: string) => void
  onRefresh?: () => void
  isDisabled?: boolean
  isLoading?: boolean
  className?: string
}

export function DeviceSelector({
  devices,
  selectedDeviceId,
  onDeviceChange,
  onRefresh,
  isDisabled = false,
  isLoading = false,
  className,
}: DeviceSelectorProps) {
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = async () => {
    if (onRefresh) {
      setIsRefreshing(true)
      try {
        await onRefresh()
      } finally {
        setTimeout(() => setIsRefreshing(false), 500)
      }
    }
  }

  // Auto-select first device if none selected
  useEffect(() => {
    if (!selectedDeviceId && devices.length > 0) {
      onDeviceChange(devices[0].deviceId)
    }
  }, [devices, selectedDeviceId, onDeviceChange])

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between">
        <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          <Mic className="inline-block w-3 h-3 mr-1" />
          Microphone
        </Label>
        {onRefresh && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={handleRefresh}
                  disabled={isDisabled || isRefreshing}
                >
                  <RefreshCw
                    className={cn(
                      'h-3.5 w-3.5',
                      isRefreshing && 'animate-spin'
                    )}
                  />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="left">
                <p>Refresh devices</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>

      <Select
        value={selectedDeviceId || undefined}
        onValueChange={onDeviceChange}
        disabled={isDisabled || isLoading}
      >
        <SelectTrigger className="w-full bg-background/50">
          <SelectValue placeholder="Select microphone" />
        </SelectTrigger>
        <SelectContent>
          {devices.length === 0 ? (
            <div className="py-4 text-center text-sm text-muted-foreground">
              No microphones found
            </div>
          ) : (
            devices.map((device) => (
              <SelectItem key={device.deviceId} value={device.deviceId}>
                <div className="flex items-center gap-2">
                  <Mic className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="truncate max-w-[200px]">
                    {device.label || `Microphone ${device.deviceId.slice(0, 8)}`}
                  </span>
                </div>
              </SelectItem>
            ))
          )}
        </SelectContent>
      </Select>

      {devices.length === 0 && (
        <p className="text-xs text-muted-foreground">
          Please allow microphone access to see available devices.
        </p>
      )}
    </div>
  )
}

export default DeviceSelector
