/**
 * Transcript List Component
 * 
 * Scrollable list of transcription lines with auto-scroll,
 * empty state, and performance optimizations.
 */

import { useRef, useEffect } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { TranscriptLine, PartialText, type TranscriptLineData } from './transcript-line'
import { cn } from '@/lib/utils'
import { Mic, FileText } from 'lucide-react'

interface TranscriptListProps {
  lines: TranscriptLineData[]
  partialText?: string
  autoScroll?: boolean
  showTimestamp?: boolean
  emptyStateMessage?: string
  className?: string
}

export function TranscriptList({
  lines,
  partialText,
  autoScroll = true,
  showTimestamp = true,
  emptyStateMessage = 'Start speaking to see text here...',
  className,
}: TranscriptListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    if (!autoScroll) return

    // Use smooth scroll for better UX
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [lines, partialText, autoScroll])

  const isEmpty = lines.length === 0 && !partialText
  const hasContent = lines.length > 0 || partialText

  return (
    <ScrollArea className={cn('h-full', className)} ref={scrollRef}>
      <div className="p-6">
        {/* Empty state */}
        {isEmpty && <EmptyState message={emptyStateMessage} />}

        {/* Transcript lines */}
        {hasContent && (
          <div className="space-y-1 max-w-3xl mx-auto">
            {lines.map((line) => (
              <TranscriptLine
                key={line.id}
                data={line}
                showTimestamp={showTimestamp}
              />
            ))}

            {/* Partial/streaming text */}
            {partialText && <PartialText text={partialText} />}

            {/* Scroll anchor */}
            <div ref={bottomRef} className="h-4" />
          </div>
        )}
      </div>
    </ScrollArea>
  )
}

/**
 * Empty state component
 */
interface EmptyStateProps {
  message: string
  className?: string
}

function EmptyState({ message, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center h-[300px] text-muted-foreground/40 gap-4',
        className
      )}
    >
      <div className="relative">
        <Mic className="w-12 h-12 opacity-20" />
        <div className="absolute -bottom-1 -right-1 bg-background rounded-full p-0.5">
          <FileText className="w-5 h-5 opacity-40" />
        </div>
      </div>
      <p className="text-lg font-medium text-center max-w-xs">{message}</p>
      <p className="text-sm text-muted-foreground/30">
        Press the microphone button or hit Space to begin
      </p>
    </div>
  )
}

/**
 * Transcript statistics
 */
interface TranscriptStatsProps {
  lines: TranscriptLineData[]
  className?: string
}

export function TranscriptStats({ lines, className }: TranscriptStatsProps) {
  const wordCount = lines.reduce((acc, line) => {
    return acc + line.text.split(/\s+/).filter(Boolean).length
  }, 0)

  const charCount = lines.reduce((acc, line) => acc + line.text.length, 0)

  const avgLatency =
    lines.length > 0
      ? Math.round(
          lines
            .filter((l) => l.latency !== undefined)
            .reduce((acc, l) => acc + (l.latency || 0), 0) /
            lines.filter((l) => l.latency !== undefined).length || 0
        )
      : 0

  return (
    <div className={cn('flex items-center gap-4 text-xs text-muted-foreground', className)}>
      <span>
        <strong>{lines.length}</strong> segments
      </span>
      <span>
        <strong>{wordCount}</strong> words
      </span>
      <span>
        <strong>{charCount}</strong> characters
      </span>
      {avgLatency > 0 && (
        <span>
          Avg latency: <strong>{avgLatency}ms</strong>
        </span>
      )}
    </div>
  )
}

export default TranscriptList
