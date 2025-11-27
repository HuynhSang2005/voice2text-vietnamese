/**
 * Model Selector Component
 * 
 * Dropdown to select ASR model for transcription.
 */

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Cpu, Loader2 } from 'lucide-react'
import { useModelStatus } from '@/hooks/useModelStatus'
import { cn } from '@/lib/utils'

interface ModelSelectorProps {
  currentModel: string
  onModelChange: (model: string) => void
  disabled?: boolean
  className?: string
}

interface ModelInfo {
  id: string
  name: string
  description: string
  speed: 'fast' | 'medium' | 'slow'
  accuracy: 'low' | 'medium' | 'high'
}

const AVAILABLE_MODELS: ModelInfo[] = [
  {
    id: 'zipformer',
    name: 'Zipformer',
    description: 'Fast streaming model',
    speed: 'fast',
    accuracy: 'medium',
  },
  {
    id: 'phowhisper',
    name: 'PhoWhisper',
    description: 'Balanced Vietnamese model',
    speed: 'medium',
    accuracy: 'high',
  },
  {
    id: 'faster-whisper',
    name: 'Faster Whisper',
    description: 'High accuracy model',
    speed: 'slow',
    accuracy: 'high',
  },
  {
    id: 'hkab',
    name: 'HKAB',
    description: 'Custom Vietnamese model',
    speed: 'medium',
    accuracy: 'high',
  },
]

const speedColors = {
  fast: 'bg-green-500/20 text-green-600',
  medium: 'bg-yellow-500/20 text-yellow-600',
  slow: 'bg-red-500/20 text-red-600',
}

const accuracyColors = {
  low: 'bg-red-500/20 text-red-600',
  medium: 'bg-yellow-500/20 text-yellow-600',
  high: 'bg-green-500/20 text-green-600',
}

export function ModelSelector({
  currentModel,
  onModelChange,
  disabled = false,
  className,
}: ModelSelectorProps) {
  const { modelStatus, isSwitchingModel } = useModelStatus()

  const selectedModelInfo = AVAILABLE_MODELS.find((m) => m.id === currentModel)
  const isLoading = isSwitchingModel || modelStatus?.status === 'loading'

  // Use all models - server doesn't expose available models list
  const displayModels = AVAILABLE_MODELS

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <Cpu className="w-4 h-4 text-muted-foreground" />
      <Select
        value={currentModel}
        onValueChange={onModelChange}
        disabled={disabled || isLoading}
      >
        <SelectTrigger className="w-[200px] h-9">
          {isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-muted-foreground">Loading...</span>
            </div>
          ) : (
            <SelectValue placeholder="Select model" />
          )}
        </SelectTrigger>
        <SelectContent>
          {displayModels.map((model) => (
            <SelectItem key={model.id} value={model.id} className="py-3">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{model.name}</span>
                  <Badge variant="outline" className={cn('text-xs', speedColors[model.speed])}>
                    {model.speed}
                  </Badge>
                </div>
                <span className="text-xs text-muted-foreground">{model.description}</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Selected model badges */}
      {selectedModelInfo && !isLoading && (
        <div className="hidden sm:flex items-center gap-1">
          <Badge variant="outline" className={cn('text-xs', accuracyColors[selectedModelInfo.accuracy])}>
            {selectedModelInfo.accuracy} accuracy
          </Badge>
        </div>
      )}
    </div>
  )
}

export default ModelSelector
