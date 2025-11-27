import { memo } from 'react'
import { TableRow, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { FileText, Clock, Eye, Copy, Trash2, MoreHorizontal } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { format } from 'date-fns'
import { cn } from '@/lib/utils'
import type { TranscriptionLog } from '@/client'

interface HistoryRowProps {
  log: TranscriptionLog
  isSelected: boolean
  onSelect: (id: number | null) => void
  onView: (log: TranscriptionLog) => void
  onCopy: (content: string) => void
  onDelete?: (id: number) => void
}

function HistoryRowComponent({
  log,
  isSelected,
  onSelect,
  onView,
  onCopy,
  onDelete,
}: HistoryRowProps) {
  const latencyColor = log.latency_ms < 500 
    ? 'text-green-500' 
    : log.latency_ms < 1000 
      ? 'text-yellow-500' 
      : 'text-red-500'

  const handleRowClick = () => {
    onSelect(isSelected ? null : log.id ?? null)
  }

  return (
    <TableRow
      className={cn(
        'group cursor-pointer transition-colors',
        isSelected 
          ? 'bg-primary/5 hover:bg-primary/10' 
          : 'hover:bg-muted/50'
      )}
      onClick={handleRowClick}
    >
      {/* Session ID */}
      <TableCell className="pl-6">
        <div className="flex items-center gap-2">
          <div className={cn(
            'p-1.5 rounded-md transition-colors',
            isSelected ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'
          )}>
            <FileText className="w-3.5 h-3.5" />
          </div>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="font-mono text-xs text-muted-foreground group-hover:text-foreground transition-colors">
                {log.session_id.slice(0, 8)}
              </span>
            </TooltipTrigger>
            <TooltipContent>
              <p className="font-mono text-xs">{log.session_id}</p>
            </TooltipContent>
          </Tooltip>
        </div>
      </TableCell>

      {/* Date & Time */}
      <TableCell>
        <div className="flex flex-col">
          <span className="text-sm font-medium text-foreground">
            {log.created_at ? format(new Date(log.created_at), 'MMM d, yyyy') : 'Unknown'}
          </span>
          <span className="text-xs text-muted-foreground">
            {log.created_at ? format(new Date(log.created_at), 'HH:mm:ss') : ''}
          </span>
        </div>
      </TableCell>

      {/* Model */}
      <TableCell>
        <Badge 
          variant="outline" 
          className="text-[10px] font-medium bg-background/50 backdrop-blur-sm"
        >
          {log.model_id}
        </Badge>
      </TableCell>

      {/* Content Preview */}
      <TableCell className="max-w-[400px]">
        <Tooltip>
          <TooltipTrigger asChild>
            <p className="truncate text-sm text-foreground/90 font-medium leading-relaxed">
              {log.content || <span className="text-muted-foreground italic">No content</span>}
            </p>
          </TooltipTrigger>
          {log.content && log.content.length > 50 && (
            <TooltipContent className="max-w-[400px]">
              <p className="text-sm whitespace-pre-wrap">{log.content}</p>
            </TooltipContent>
          )}
        </Tooltip>
      </TableCell>

      {/* Latency */}
      <TableCell>
        {log.latency_ms > 0 ? (
          <div className="flex items-center gap-1.5">
            <Clock className="w-3 h-3 text-muted-foreground/50" />
            <span className={cn('font-mono text-xs font-bold', latencyColor)}>
              {log.latency_ms.toFixed(0)}ms
            </span>
          </div>
        ) : (
          <span className="text-muted-foreground text-xs">-</span>
        )}
      </TableCell>

      {/* Actions */}
      <TableCell className="text-right pr-6">
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={(e) => {
                  e.stopPropagation()
                  onView(log)
                }}
              >
                <Eye className="w-3.5 h-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>View details</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={(e) => {
                  e.stopPropagation()
                  onCopy(log.content)
                }}
              >
                <Copy className="w-3.5 h-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Copy transcript</TooltipContent>
          </Tooltip>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreHorizontal className="w-3.5 h-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onView(log)}>
                <Eye className="w-4 h-4 mr-2" />
                View Details
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onCopy(log.content)}>
                <Copy className="w-4 h-4 mr-2" />
                Copy Transcript
              </DropdownMenuItem>
              {onDelete && log.id && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={() => onDelete(log.id!)}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </TableCell>
    </TableRow>
  )
}

export const HistoryRow = memo(HistoryRowComponent)
