/**
 * Common Model Selector Component
 * 
 * Reusable dropdown to select ASR model with loading states,
 * error handling, and model status indicators.
 */

import { useQuery } from '@tanstack/react-query'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Cpu, Loader2, AlertCircle, Zap, Target, Clock } from 'lucide-react'
import { getModelsOptions } from '@/client/@tanstack/react-query.gen'
import { cn } from '@/lib/utils'

type ModelSpeed = 'fast' | 'medium' | 'slow'
type ModelAccuracy = 'low' | 'medium' | 'high'

interface ModelMetadata {
  speed: ModelSpeed
  accuracy: ModelAccuracy
  description: string
}

// Static metadata for known models
const MODEL_METADATA: Record<string, ModelMetadata> = {
  zipformer: {
    speed: 'fast',
    accuracy: 'medium',
    description: 'Fast streaming model optimized for real-time',
  },
  phowhisper: {
    speed: 'medium',
    accuracy: 'high',
    description: 'Balanced Vietnamese speech recognition',
  },
  'faster-whisper': {
    speed: 'slow',
    accuracy: 'high',
    description: 'High accuracy with CTranslate2 optimization',
  },
  hkab: {
    speed: 'medium',
    accuracy: 'high',
    description: 'Custom Vietnamese model by HKAB',
  },
}

const SPEED_CONFIG = {
  fast: { label: 'Fast', icon: Zap, color: 'text-green-500 bg-green-500/10' },
  medium: { label: 'Medium', icon: Clock, color: 'text-yellow-500 bg-yellow-500/10' },
  slow: { label: 'Slow', icon: Clock, color: 'text-orange-500 bg-orange-500/10' },
}

const ACCURACY_CONFIG = {
  low: { label: 'Low', color: 'text-red-500 bg-red-500/10' },
  medium: { label: 'Medium', color: 'text-yellow-500 bg-yellow-500/10' },
  high: { label: 'High', color: 'text-green-500 bg-green-500/10' },
}

interface CommonModelSelectorProps {
  value: string
  onValueChange: (model: string) => void
  disabled?: boolean
  isLoading?: boolean
  showIcon?: boolean
  showBadges?: boolean
  size?: 'sm' | 'default'
  className?: string
}

export function CommonModelSelector({
  value,
  onValueChange,
  disabled = false,
  isLoading = false,
  showIcon = true,
  showBadges = true,
  size = 'default',
  className,
}: CommonModelSelectorProps) {
  // Fetch models from API
  const { 
    data: models, 
    isLoading: isLoadingModels, 
    isError,
    error 
  } = useQuery({
    ...getModelsOptions(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    retry: 2,
  })

  const selectedMeta = MODEL_METADATA[value]
  const isDisabled = disabled || isLoading || isLoadingModels

  // Loading state
  if (isLoadingModels) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        {showIcon && <Cpu className="w-4 h-4 text-muted-foreground" />}
        <Skeleton className={cn('w-[180px]', size === 'sm' ? 'h-8' : 'h-9')} />
      </div>
    )
  }

  // Error state
  if (isError) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className={cn('flex items-center gap-2 text-destructive', className)}>
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">Failed to load models</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>{error?.message || 'Could not fetch available models'}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {showIcon && <Cpu className="w-4 h-4 text-muted-foreground" />}
      
      <Select
        value={value}
        onValueChange={onValueChange}
        disabled={isDisabled}
      >
        <SelectTrigger className={cn(
          'min-w-[180px]',
          size === 'sm' ? 'h-8 text-sm' : 'h-9'
        )}>
          {isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-muted-foreground">Switching...</span>
            </div>
          ) : (
            <SelectValue placeholder="Select model" />
          )}
        </SelectTrigger>
        <SelectContent>
          {models?.map((model) => {
            const meta = MODEL_METADATA[model.id]
            const SpeedIcon = meta ? SPEED_CONFIG[meta.speed].icon : Clock
            
            return (
              <SelectItem 
                key={model.id} 
                value={model.id} 
                className="py-3"
              >
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{model.name}</span>
                    {meta && (
                      <Badge 
                        variant="outline" 
                        className={cn('text-xs gap-1', SPEED_CONFIG[meta.speed].color)}
                      >
                        <SpeedIcon className="w-3 h-3" />
                        {meta.speed}
                      </Badge>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {meta?.description || model.description}
                  </span>
                </div>
              </SelectItem>
            )
          })}

          {/* Show fallback options if API returns empty */}
          {(!models || models.length === 0) && (
            <>
              {Object.entries(MODEL_METADATA).map(([id, meta]) => (
                <SelectItem key={id} value={id} className="py-3">
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium capitalize">{id}</span>
                      <Badge 
                        variant="outline" 
                        className={cn('text-xs', SPEED_CONFIG[meta.speed].color)}
                      >
                        {meta.speed}
                      </Badge>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {meta.description}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </>
          )}
        </SelectContent>
      </Select>

      {/* Selected model accuracy badge (optional) */}
      {showBadges && selectedMeta && !isLoading && (
        <div className="hidden sm:flex items-center gap-1">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge 
                  variant="outline" 
                  className={cn('text-xs gap-1', ACCURACY_CONFIG[selectedMeta.accuracy].color)}
                >
                  <Target className="w-3 h-3" />
                  {selectedMeta.accuracy}
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p>Model accuracy level</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      )}
    </div>
  )
}

export default CommonModelSelector
