import { useState, useCallback, useMemo } from 'react'
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import type { TranscriptionLog } from '@/client'
import { HistoryRow } from './row'
import { EmptyState } from './empty-state'

type SortField = 'created_at' | 'latency_ms' | 'model_id'
type SortOrder = 'asc' | 'desc'

interface HistoryTableNewProps {
  history: TranscriptionLog[] | undefined
  isLoading: boolean
  isError: boolean
  searchQuery?: string
  onClearFilters?: () => void
  onViewDetail: (log: TranscriptionLog) => void
}

interface SortConfig {
  field: SortField
  order: SortOrder
}

function SortableHeader({
  field,
  label,
  currentSort,
  onSort,
  className,
}: {
  field: SortField
  label: string
  currentSort: SortConfig
  onSort: (field: SortField) => void
  className?: string
}) {
  const isActive = currentSort.field === field
  
  return (
    <TableHead className={className}>
      <Button
        variant="ghost"
        size="sm"
        className="-ml-3 h-8 data-[state=open]:bg-accent"
        onClick={() => onSort(field)}
      >
        {label}
        {isActive ? (
          currentSort.order === 'asc' ? (
            <ArrowUp className="ml-2 h-4 w-4" />
          ) : (
            <ArrowDown className="ml-2 h-4 w-4" />
          )
        ) : (
          <ArrowUpDown className="ml-2 h-4 w-4 opacity-50" />
        )}
      </Button>
    </TableHead>
  )
}

function LoadingSkeleton() {
  return (
    <TableBody>
      {Array.from({ length: 5 }).map((_, i) => (
        <TableRow key={i}>
          <td className="pl-6 py-4">
            <div className="flex items-center gap-2">
              <Skeleton className="h-7 w-7 rounded-md" />
              <Skeleton className="h-4 w-16" />
            </div>
          </td>
          <td className="py-4">
            <div className="space-y-1">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-16" />
            </div>
          </td>
          <td className="py-4">
            <Skeleton className="h-5 w-20 rounded-full" />
          </td>
          <td className="py-4">
            <Skeleton className="h-4 w-full max-w-[300px]" />
          </td>
          <td className="py-4">
            <Skeleton className="h-4 w-14" />
          </td>
          <td className="pr-6 py-4">
            <Skeleton className="h-7 w-20 ml-auto" />
          </td>
        </TableRow>
      ))}
    </TableBody>
  )
}

export function HistoryTableNew({
  history,
  isLoading,
  isError,
  searchQuery,
  onClearFilters,
  onViewDetail,
}: HistoryTableNewProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'created_at',
    order: 'desc',
  })

  const handleSort = useCallback((field: SortField) => {
    setSortConfig((prev) => ({
      field,
      order: prev.field === field && prev.order === 'desc' ? 'asc' : 'desc',
    }))
  }, [])

  const sortedHistory = useMemo(() => {
    if (!history) return []

    return [...history].sort((a, b) => {
      const { field, order } = sortConfig
      let comparison = 0

      switch (field) {
        case 'created_at':
          comparison = new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime()
          break
        case 'latency_ms':
          comparison = a.latency_ms - b.latency_ms
          break
        case 'model_id':
          comparison = a.model_id.localeCompare(b.model_id)
          break
      }

      return order === 'asc' ? comparison : -comparison
    })
  }, [history, sortConfig])

  const handleCopy = useCallback(async (content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      toast.success('Copied to clipboard')
    } catch {
      toast.error('Failed to copy')
    }
  }, [])

  const handleSelect = useCallback((id: number | null) => {
    setSelectedId(id)
  }, [])

  // Determine empty state type
  const getEmptyStateType = () => {
    if (isError) return 'error'
    if (searchQuery || history?.length === 0) return 'no-results'
    return 'no-data'
  }

  const showEmptyState = !isLoading && (!history || history.length === 0 || isError)

  return (
    <TooltipProvider>
      <Table>
        <TableHeader className="bg-muted/30 sticky top-0 z-10 backdrop-blur-md">
          <TableRow className="hover:bg-transparent border-b border-border/60">
            <TableHead className="w-[160px] pl-6">Session ID</TableHead>
            <SortableHeader
              field="created_at"
              label="Date & Time"
              currentSort={sortConfig}
              onSort={handleSort}
              className="w-[180px]"
            />
            <SortableHeader
              field="model_id"
              label="Model"
              currentSort={sortConfig}
              onSort={handleSort}
              className="w-[150px]"
            />
            <TableHead>Transcript</TableHead>
            <SortableHeader
              field="latency_ms"
              label="Latency"
              currentSort={sortConfig}
              onSort={handleSort}
              className="w-[120px]"
            />
            <TableHead className="w-[120px] text-right pr-6">Actions</TableHead>
          </TableRow>
        </TableHeader>

        {isLoading ? (
          <LoadingSkeleton />
        ) : showEmptyState ? (
          <TableBody>
            <tr>
              <td colSpan={6}>
                <EmptyState
                  type={getEmptyStateType()}
                  searchQuery={searchQuery}
                  onClearFilters={onClearFilters}
                />
              </td>
            </tr>
          </TableBody>
        ) : (
          <TableBody>
            {sortedHistory.map((log) => (
              <HistoryRow
                key={log.id ?? log.session_id}
                log={log}
                isSelected={selectedId === log.id}
                onSelect={handleSelect}
                onView={onViewDetail}
                onCopy={handleCopy}
              />
            ))}
          </TableBody>
        )}
      </Table>
    </TooltipProvider>
  )
}
