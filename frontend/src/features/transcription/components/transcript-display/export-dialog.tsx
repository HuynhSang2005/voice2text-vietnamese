/**
 * Export Dialog Component
 * 
 * Dialog for exporting transcripts in various formats:
 * - TXT: Plain text
 * - SRT: Subtitle format
 * - JSON: Structured data
 */

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Download, FileText, FileJson, Captions, Copy, Check } from 'lucide-react'
// import { cn } from '@/lib/utils'
import type { TranscriptLineData } from './transcript-line'

type ExportFormat = 'txt' | 'srt' | 'json'

interface ExportDialogProps {
  lines: TranscriptLineData[]
  sessionId?: string
  disabled?: boolean
  trigger?: React.ReactNode
}

export function ExportDialog({
  lines,
  sessionId,
  disabled = false,
  trigger,
}: ExportDialogProps) {
  const [open, setOpen] = useState(false)
  const [format, setFormat] = useState<ExportFormat>('txt')
  const [includeTimestamps, setIncludeTimestamps] = useState(true)
  const [copied, setCopied] = useState(false)

  const handleExport = () => {
    const content = generateExportContent(lines, format, includeTimestamps)
    const filename = generateFilename(sessionId, format)
    downloadFile(content, filename, getMimeType(format))
    setOpen(false)
  }

  const handleCopyToClipboard = async () => {
    const content = generateExportContent(lines, format, includeTimestamps)
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm" disabled={disabled || lines.length === 0}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Export Transcript</DialogTitle>
          <DialogDescription>
            Choose a format and download your transcription.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Format selection */}
          <div className="space-y-2">
            <Label>Export Format</Label>
            <Select value={format} onValueChange={(v) => setFormat(v as ExportFormat)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="txt">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Plain Text (.txt)
                  </div>
                </SelectItem>
                <SelectItem value="srt">
                  <div className="flex items-center gap-2">
                    <Captions className="h-4 w-4" />
                    Subtitle (.srt)
                  </div>
                </SelectItem>
                <SelectItem value="json">
                  <div className="flex items-center gap-2">
                    <FileJson className="h-4 w-4" />
                    JSON (.json)
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Options */}
          {format !== 'json' && (
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="timestamps">Include Timestamps</Label>
                <p className="text-xs text-muted-foreground">
                  Add time markers to each line
                </p>
              </div>
              <Switch
                id="timestamps"
                checked={includeTimestamps}
                onCheckedChange={setIncludeTimestamps}
              />
            </div>
          )}

          {/* Preview */}
          <div className="space-y-2">
            <Label>Preview</Label>
            <div className="bg-muted/50 rounded-md p-3 max-h-[200px] overflow-auto">
              <pre className="text-xs font-mono whitespace-pre-wrap">
                {generateExportContent(lines.slice(0, 3), format, includeTimestamps)}
                {lines.length > 3 && '\n...'}
              </pre>
            </div>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>{lines.length} segments</span>
            <span>
              {lines.reduce((acc, l) => acc + l.text.split(/\s+/).length, 0)} words
            </span>
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button variant="outline" onClick={handleCopyToClipboard} className="flex-1">
            {copied ? (
              <>
                <Check className="h-4 w-4 mr-2 text-green-500" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="h-4 w-4 mr-2" />
                Copy to Clipboard
              </>
            )}
          </Button>
          <Button onClick={handleExport} className="flex-1">
            <Download className="h-4 w-4 mr-2" />
            Download {format.toUpperCase()}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

/**
 * Generate export content based on format
 */
function generateExportContent(
  lines: TranscriptLineData[],
  format: ExportFormat,
  includeTimestamps: boolean
): string {
  switch (format) {
    case 'txt':
      return lines
        .map((line) => {
          if (includeTimestamps) {
            const time = formatTime(line.timestamp)
            return `[${time}] ${line.text}`
          }
          return line.text
        })
        .join('\n\n')

    case 'srt':
      return lines
        .map((line, index) => {
          const startTime = formatSrtTime(line.timestamp)
          // Estimate end time (2 seconds after start, or use next line's timestamp)
          const endTime = formatSrtTime(
            lines[index + 1]?.timestamp || line.timestamp + 2000
          )
          return `${index + 1}\n${startTime} --> ${endTime}\n${line.text}`
        })
        .join('\n\n')

    case 'json':
      return JSON.stringify(
        {
          exportedAt: new Date().toISOString(),
          segments: lines.map((line) => ({
            id: line.id,
            text: line.text,
            timestamp: line.timestamp,
            isoTime: new Date(line.timestamp).toISOString(),
            latency: line.latency,
          })),
          stats: {
            totalSegments: lines.length,
            totalWords: lines.reduce(
              (acc, l) => acc + l.text.split(/\s+/).filter(Boolean).length,
              0
            ),
            totalCharacters: lines.reduce((acc, l) => acc + l.text.length, 0),
          },
        },
        null,
        2
      )

    default:
      return ''
  }
}

function generateFilename(sessionId: string | undefined, format: ExportFormat): string {
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')
  const prefix = sessionId ? `transcript_${sessionId.slice(0, 8)}` : 'transcript'
  return `${prefix}_${timestamp}.${format}`
}

function getMimeType(format: ExportFormat): string {
  switch (format) {
    case 'txt':
      return 'text/plain'
    case 'srt':
      return 'application/x-subrip'
    case 'json':
      return 'application/json'
    default:
      return 'text/plain'
  }
}

function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatSrtTime(timestamp: number): string {
  const date = new Date(timestamp)
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  const ms = String(date.getMilliseconds()).padStart(3, '0')
  return `${hours}:${minutes}:${seconds},${ms}`
}

export default ExportDialog
