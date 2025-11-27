/**
 * Transcript Line Component
 * 
 * Single line of transcription with timestamp, copy functionality,
 * and visual indicators for partial/final status.
 */

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Copy, Check, Clock } from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

export interface TranscriptLineData {
  id: string
  text: string
  timestamp: number // Unix timestamp in milliseconds
  isFinal: boolean
  latency?: number // Processing latency in ms
}

interface TranscriptLineProps {
  data: TranscriptLineData
  showTimestamp?: boolean
  showCopy?: boolean
  className?: string
}

export function TranscriptLine({
  data,
  showTimestamp = true,
  showCopy = true,
  className,
}: TranscriptLineProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(data.text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy text:', error)
    }
  }

  const formattedTime = formatTimestamp(data.timestamp)

  return (
    <div
      className={cn(
        'group relative pl-4 py-2 transition-colors',
        data.isFinal
          ? 'border-l-2 border-primary/20 hover:border-primary hover:bg-accent/30'
          : 'border-l-2 border-primary animate-pulse',
        className
      )}
    >
      {/* Timestamp */}
      {showTimestamp && data.isFinal && (
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs text-muted-foreground font-mono flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formattedTime}
          </span>
          {data.latency !== undefined && (
            <span className="text-xs text-muted-foreground/60">
              ({data.latency}ms)
            </span>
          )}
        </div>
      )}

      {/* Text content */}
      <p
        className={cn(
          'text-lg leading-relaxed pr-10',
          data.isFinal ? 'text-foreground/90' : 'text-muted-foreground italic'
        )}
      >
        {data.text}
      </p>

      {/* Copy button (visible on hover for final text) */}
      {showCopy && data.isFinal && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className={cn(
                  'absolute right-2 top-1/2 -translate-y-1/2 h-7 w-7',
                  'opacity-0 group-hover:opacity-100 transition-opacity'
                )}
                onClick={handleCopy}
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-green-500" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{copied ? 'Copied!' : 'Copy text'}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}

      {/* Active indicator dot */}
      <span
        className={cn(
          'absolute -left-[5px] top-4 w-2 h-2 rounded-full transition-all',
          data.isFinal
            ? 'bg-primary/20 group-hover:bg-primary group-hover:scale-125'
            : 'bg-primary animate-pulse'
        )}
      />
    </div>
  )
}

/**
 * Partial text indicator (for currently processing text)
 */
interface PartialTextProps {
  text: string
  className?: string
}

export function PartialText({ text, className }: PartialTextProps) {
  if (!text) return null

  return (
    <div
      className={cn(
        'pl-4 py-2 border-l-2 border-primary animate-pulse',
        className
      )}
    >
      <p className="text-lg leading-relaxed text-muted-foreground italic">
        {text}
        <span className="inline-block w-2 h-5 ml-1 bg-primary/50 animate-pulse" />
      </p>
    </div>
  )
}

/**
 * Format timestamp to readable time
 */
function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export default TranscriptLine
