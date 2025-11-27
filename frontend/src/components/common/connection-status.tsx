/**
 * Connection Status Component
 * 
 * Displays WebSocket connection status with visual indicators
 * and optional reconnect button.
 */

import { cn } from '@/lib/utils'
import { useAppStore } from '@/store'
import { Button } from '@/components/ui/button'
import { 
  Tooltip, 
  TooltipContent, 
  TooltipProvider, 
  TooltipTrigger 
} from '@/components/ui/tooltip'
import { Wifi, WifiOff, Loader2, AlertCircle } from 'lucide-react'

type WsState = 'connecting' | 'open' | 'closing' | 'closed'

interface StatusConfig {
  icon: React.ComponentType<{ className?: string }>
  label: string
  color: string
  dotColor: string
  animate?: boolean
}

const statusConfig: Record<WsState, StatusConfig> = {
  connecting: {
    icon: Loader2,
    label: 'Connecting...',
    color: 'text-yellow-500',
    dotColor: 'bg-yellow-500',
    animate: true,
  },
  open: {
    icon: Wifi,
    label: 'Connected',
    color: 'text-green-500',
    dotColor: 'bg-green-500',
  },
  closing: {
    icon: AlertCircle,
    label: 'Disconnecting...',
    color: 'text-orange-500',
    dotColor: 'bg-orange-500',
  },
  closed: {
    icon: WifiOff,
    label: 'Disconnected',
    color: 'text-red-500',
    dotColor: 'bg-red-500',
  },
}

interface ConnectionStatusProps {
  className?: string
  showLabel?: boolean
  showReconnectButton?: boolean
  onReconnect?: () => void
}

export function ConnectionStatus({
  className,
  showLabel = true,
  showReconnectButton = true,
  onReconnect,
}: ConnectionStatusProps) {
  const wsState = useAppStore((s) => s.wsState)
  const reconnectAttempts = useAppStore((s) => s.reconnectAttempts)
  
  const config = statusConfig[wsState]
  const Icon = config.icon

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={cn('flex items-center gap-2', className)}>
            {/* Status Dot */}
            <span className="relative flex h-2.5 w-2.5">
              {wsState === 'connecting' && (
                <span className={cn(
                  'absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping',
                  config.dotColor
                )} />
              )}
              <span className={cn(
                'relative inline-flex rounded-full h-2.5 w-2.5',
                config.dotColor
              )} />
            </span>

            {/* Icon */}
            <Icon className={cn(
              'h-4 w-4',
              config.color,
              config.animate && 'animate-spin'
            )} />

            {/* Label (desktop only) */}
            {showLabel && (
              <span className={cn(
                'hidden sm:inline text-sm font-medium',
                config.color
              )}>
                {config.label}
              </span>
            )}

            {/* Reconnect Button */}
            {showReconnectButton && wsState === 'closed' && onReconnect && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onReconnect}
                className="h-7 px-2 text-xs"
              >
                Reconnect
              </Button>
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <div className="text-sm">
            <p className="font-medium">{config.label}</p>
            {reconnectAttempts > 0 && wsState === 'closed' && (
              <p className="text-muted-foreground text-xs mt-1">
                Reconnect attempts: {reconnectAttempts}
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

/**
 * Compact connection status (just dot + icon)
 */
export function ConnectionStatusCompact({ className }: { className?: string }) {
  return (
    <ConnectionStatus 
      className={className} 
      showLabel={false} 
      showReconnectButton={false} 
    />
  )
}

export default ConnectionStatus
