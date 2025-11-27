/**
 * Volume Meter Component
 * 
 * Real-time audio level visualization with smooth animations.
 */

import { useMemo } from 'react'
import { cn } from '@/lib/utils'
import { Volume2, VolumeX } from 'lucide-react'

interface VolumeMeterProps {
  volume: number
  isActive?: boolean
  showLabel?: boolean
  showIcon?: boolean
  variant?: 'bar' | 'gradient' | 'segments'
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function VolumeMeter({
  volume,
  isActive = false,
  showLabel = true,
  showIcon = true,
  variant = 'bar',
  size = 'md',
  className,
}: VolumeMeterProps) {
  // Clamp volume between 0-100
  const clampedVolume = Math.max(0, Math.min(100, volume))
  
  // Determine volume level for color
  const volumeLevel = useMemo(() => {
    if (clampedVolume < 30) return 'low'
    if (clampedVolume < 70) return 'medium'
    return 'high'
  }, [clampedVolume])

  const heightClasses = {
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-3',
  }

  // Render different variants
  if (variant === 'segments') {
    return (
      <VolumeSegments
        volume={clampedVolume}
        isActive={isActive}
        showLabel={showLabel}
        showIcon={showIcon}
        size={size}
        className={className}
      />
    )
  }

  if (variant === 'gradient') {
    return (
      <div className={cn('space-y-2', className)}>
        {showLabel && (
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              {showIcon && (
                isActive ? (
                  <Volume2 className="h-3.5 w-3.5" />
                ) : (
                  <VolumeX className="h-3.5 w-3.5" />
                )
              )}
              Input Level
            </span>
            <span className="font-mono">{Math.round(clampedVolume)}%</span>
          </div>
        )}
        <div className={cn('bg-secondary rounded-full overflow-hidden', heightClasses[size])}>
          <div
            className={cn(
              'h-full transition-all duration-75 ease-out rounded-full',
              isActive
                ? 'bg-gradient-to-r from-green-500 via-yellow-500 to-red-500'
                : 'bg-muted-foreground/30'
            )}
            style={{ width: `${clampedVolume}%` }}
          />
        </div>
      </div>
    )
  }

  // Default bar variant
  return (
    <div className={cn('space-y-2', className)}>
      {showLabel && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            {showIcon && (
              isActive ? (
                <Volume2 className="h-3.5 w-3.5" />
              ) : (
                <VolumeX className="h-3.5 w-3.5" />
              )
            )}
            Input Level
          </span>
          <span className="font-mono">{Math.round(clampedVolume)}%</span>
        </div>
      )}
      <div className={cn('bg-secondary rounded-full overflow-hidden', heightClasses[size])}>
        <div
          className={cn(
            'h-full transition-all duration-75 ease-out rounded-full',
            isActive ? getVolumeColor(volumeLevel) : 'bg-muted-foreground/30'
          )}
          style={{ width: `${clampedVolume}%` }}
        />
      </div>
    </div>
  )
}

/**
 * Segmented volume meter (like professional audio software)
 */
interface VolumeSegmentsProps {
  volume: number
  isActive?: boolean
  showLabel?: boolean
  showIcon?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
  segmentCount?: number
}

export function VolumeSegments({
  volume,
  isActive = false,
  showLabel = true,
  showIcon = true,
  size = 'md',
  className,
  segmentCount = 20,
}: VolumeSegmentsProps) {
  const activeSegments = Math.floor((volume / 100) * segmentCount)

  const segmentHeights = {
    sm: 'h-3',
    md: 'h-4',
    lg: 'h-6',
  }

  return (
    <div className={cn('space-y-2', className)}>
      {showLabel && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            {showIcon && (
              isActive ? (
                <Volume2 className="h-3.5 w-3.5" />
              ) : (
                <VolumeX className="h-3.5 w-3.5" />
              )
            )}
            Input Level
          </span>
          <span className="font-mono">{Math.round(volume)}%</span>
        </div>
      )}
      <div className="flex gap-0.5">
        {Array.from({ length: segmentCount }).map((_, index) => {
          const isSegmentActive = index < activeSegments
          const segmentPercent = (index / segmentCount) * 100
          
          let colorClass = 'bg-muted-foreground/20'
          if (isSegmentActive && isActive) {
            if (segmentPercent < 60) colorClass = 'bg-green-500'
            else if (segmentPercent < 80) colorClass = 'bg-yellow-500'
            else colorClass = 'bg-red-500'
          }

          return (
            <div
              key={index}
              className={cn(
                'flex-1 rounded-sm transition-colors duration-75',
                segmentHeights[size],
                colorClass
              )}
            />
          )
        })}
      </div>
    </div>
  )
}

function getVolumeColor(level: 'low' | 'medium' | 'high'): string {
  switch (level) {
    case 'low':
      return 'bg-green-500'
    case 'medium':
      return 'bg-primary'
    case 'high':
      return 'bg-destructive'
  }
}

export default VolumeMeter
