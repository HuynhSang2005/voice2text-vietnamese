/**
 * Recorder Button Component
 * 
 * Main record/stop button with pulse animation and visual feedback.
 * Supports keyboard shortcut (Space) and accessibility.
 */

import { useCallback, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Mic, MicOff, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface RecorderButtonProps {
  isRecording: boolean
  isConnected: boolean
  isLoading?: boolean
  volume?: number
  onToggle: () => void
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeClasses = {
  sm: 'h-16 w-16',
  md: 'h-20 w-20',
  lg: 'h-24 w-24',
}

const iconSizes = {
  sm: 'w-6 h-6',
  md: 'w-8 h-8',
  lg: 'w-10 h-10',
}

export function RecorderButton({
  isRecording,
  isConnected,
  isLoading = false,
  volume = 0,
  onToggle,
  size = 'lg',
  className,
}: RecorderButtonProps) {
  // Keyboard shortcut: Space to toggle recording
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Only trigger if not typing in an input
      if (
        event.code === 'Space' &&
        event.target === document.body &&
        isConnected &&
        !isLoading
      ) {
        event.preventDefault()
        onToggle()
      }
    },
    [isConnected, isLoading, onToggle]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  // Calculate pulse scale based on volume
  const pulseScale = 1 + (volume / 100) * 0.3

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={cn('relative flex items-center justify-center', className)}>
            {/* Pulse rings when recording */}
            {isRecording && !isLoading && (
              <>
                {/* Outer pulse ring */}
                <div
                  className="absolute rounded-full bg-destructive/20 animate-ping"
                  style={{
                    width: '100%',
                    height: '100%',
                    transform: `scale(${pulseScale})`,
                    animationDuration: '1.5s',
                  }}
                />
                {/* Inner pulse ring */}
                <div
                  className="absolute rounded-full bg-destructive/10 animate-pulse"
                  style={{
                    width: '100%',
                    height: '100%',
                    transform: `scale(${pulseScale * 1.2})`,
                    animationDuration: '1s',
                  }}
                />
              </>
            )}

            {/* Main button */}
            <Button
              size="lg"
              disabled={!isConnected || isLoading}
              onClick={onToggle}
              aria-label={isRecording ? 'Stop recording' : 'Start recording'}
              aria-pressed={isRecording}
              className={cn(
                'rounded-full shadow-2xl transition-all duration-300 border-4',
                sizeClasses[size],
                isRecording
                  ? 'bg-destructive hover:bg-destructive/90 border-destructive/30'
                  : 'bg-primary hover:bg-primary/90 border-primary/30',
                isConnected && !isLoading && 'hover:scale-105 active:scale-95',
                !isConnected && 'opacity-50 cursor-not-allowed'
              )}
            >
              {isLoading ? (
                <Loader2 className={cn(iconSizes[size], 'animate-spin')} />
              ) : isRecording ? (
                <MicOff className={iconSizes[size]} />
              ) : (
                <Mic className={cn(iconSizes[size], 'text-primary-foreground')} />
              )}
            </Button>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <p className="font-medium">
            {!isConnected
              ? 'Waiting for connection...'
              : isLoading
                ? 'Processing...'
                : isRecording
                  ? 'Click to stop (Space)'
                  : 'Click to record (Space)'}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

/**
 * Recording status text component
 */
interface RecordingStatusProps {
  isRecording: boolean
  isConnected: boolean
  className?: string
}

export function RecordingStatus({
  isRecording,
  isConnected,
  className,
}: RecordingStatusProps) {
  return (
    <div className={cn('text-center space-y-1', className)}>
      <h3
        className={cn(
          'font-semibold text-lg transition-colors',
          isRecording ? 'text-destructive' : 'text-foreground'
        )}
      >
        {!isConnected
          ? 'Disconnected'
          : isRecording
            ? 'Recording...'
            : 'Ready to Record'}
      </h3>
      <p className="text-xs text-muted-foreground">
        {!isConnected
          ? 'Connect to start recording'
          : isRecording
            ? 'Listening to audio stream'
            : 'Click microphone to start'}
      </p>
    </div>
  )
}

export default RecorderButton
