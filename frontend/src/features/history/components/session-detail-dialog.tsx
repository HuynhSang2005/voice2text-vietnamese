import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  FileText,
  Clock,
  Calendar,
  Cpu,
  Copy,
  Download,
  Check,
  ChevronDown,
} from 'lucide-react'
import { format as formatDate } from 'date-fns'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import type { TranscriptionLog } from '@/client'

interface SessionDetailDialogProps {
  log: TranscriptionLog | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

type ExportFormat = 'txt' | 'json' | 'srt'

export function SessionDetailDialog({
  log,
  open,
  onOpenChange,
}: SessionDetailDialogProps) {
  const [copied, setCopied] = useState(false)

  if (!log) return null

  const latencyColor = log.latency_ms < 500
    ? 'text-green-500'
    : log.latency_ms < 1000
      ? 'text-yellow-500'
      : 'text-red-500'

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(log.content)
      setCopied(true)
      toast.success('Transcript copied to clipboard')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Failed to copy transcript')
    }
  }

  const handleExport = (exportFormat: ExportFormat) => {
    let content: string
    let filename: string
    let mimeType: string

    const dateStr = log.created_at
      ? formatDate(new Date(log.created_at), 'yyyy-MM-dd_HHmmss')
      : 'unknown'

    switch (exportFormat) {
      case 'txt':
        content = log.content
        filename = `transcript_${dateStr}.txt`
        mimeType = 'text/plain'
        break
      case 'json':
        content = JSON.stringify(
          {
            session_id: log.session_id,
            model_id: log.model_id,
            content: log.content,
            latency_ms: log.latency_ms,
            created_at: log.created_at,
          },
          null,
          2
        )
        filename = `transcript_${dateStr}.json`
        mimeType = 'application/json'
        break
      case 'srt':
        content = `1\n00:00:00,000 --> 00:00:30,000\n${log.content}\n`
        filename = `transcript_${dateStr}.srt`
        mimeType = 'text/srt'
        break
    }

    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    toast.success(`Exported as ${exportFormat.toUpperCase()}`)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary" />
            Session Details
          </DialogTitle>
          <DialogDescription>
            View and export your transcription session
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-4 py-4">
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <FileText className="w-3 h-3" />
                Session ID
              </p>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <p className="text-sm font-mono truncate cursor-help">
                      {log.session_id}
                    </p>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="font-mono text-xs">{log.session_id}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>

            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                Date & Time
              </p>
              <p className="text-sm">
                {log.created_at
                  ? formatDate(new Date(log.created_at), 'PPpp')
                  : 'Unknown'}
              </p>
            </div>

            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <Cpu className="w-3 h-3" />
                Model
              </p>
              <Badge variant="outline" className="text-xs">
                {log.model_id}
              </Badge>
            </div>

            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Latency
              </p>
              {log.latency_ms > 0 ? (
                <p className={cn('text-sm font-mono font-semibold', latencyColor)}>
                  {log.latency_ms.toFixed(0)}ms
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">-</p>
              )}
            </div>
          </div>

          <Separator />

          {/* Transcript Content */}
          <div className="py-4 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Transcript</p>
              <p className="text-xs text-muted-foreground">
                {log.content.length} characters
              </p>
            </div>
            <ScrollArea className="h-[200px] rounded-md border bg-muted/30 p-4">
              <p className="text-sm leading-relaxed whitespace-pre-wrap">
                {log.content || (
                  <span className="text-muted-foreground italic">
                    No transcript content available
                  </span>
                )}
              </p>
            </ScrollArea>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-4 border-t">
          <Button variant="outline" size="sm" onClick={handleCopy}>
            {copied ? (
              <>
                <Check className="w-4 h-4 mr-2" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 mr-2" />
                Copy
              </>
            )}
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="default" size="sm">
                <Download className="w-4 h-4 mr-2" />
                Export
                <ChevronDown className="w-4 h-4 ml-1" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => handleExport('txt')}>
                Export as TXT
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExport('json')}>
                Export as JSON
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExport('srt')}>
                Export as SRT
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </DialogContent>
    </Dialog>
  )
}
