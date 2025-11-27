import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight, History as HistoryIcon } from 'lucide-react'
import { getHistoryOptions, getModelsOptions } from '@/client/@tanstack/react-query.gen'
import type { TranscriptionLog } from '@/client'
import { useHistoryFilters } from './hooks/use-history-filters'
import { HistoryFiltersNew } from './components/history-filters-new'
import { HistoryTableNew } from './components/history-table'
import { SessionDetailDialog } from './components/session-detail-dialog'

export default function HistoryPage() {
  const [selectedLog, setSelectedLog] = useState<TranscriptionLog | null>(null)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)

  const {
    filters,
    queryParams,
    hasActiveFilters,
    activeFilterCount,
    setSearch,
    setModelId,
    setDateRange,
    setPage,
    clearFilters,
  } = useHistoryFilters()

  const {
    data: history,
    isLoading,
    isError,
  } = useQuery({
    ...getHistoryOptions({
      query: {
        page: queryParams.page,
        limit: queryParams.limit,
        search: queryParams.search,
        model: queryParams.model,
      },
    }),
  })

  const { data: models } = useQuery({
    ...getModelsOptions(),
  })

  const handleViewDetail = (log: TranscriptionLog) => {
    setSelectedLog(log)
    setDetailDialogOpen(true)
  }

  const handleClearFilters = () => {
    clearFilters()
  }

  const hasMore = !!history && history.length >= filters.limit

  return (
    <div className="flex flex-col h-full gap-6 max-w-[1600px] mx-auto p-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <HistoryIcon className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-foreground">
                Transcription History
              </h1>
              <p className="text-muted-foreground text-sm">
                Review and manage your past transcription sessions
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-card border rounded-lg px-4 py-2 shadow-sm">
            <span className="text-sm font-medium text-muted-foreground">
              Total Sessions:
            </span>
            <Badge variant="secondary" className="h-6 px-2.5 text-sm font-bold">
              {isLoading ? '...' : history?.length || 0}
            </Badge>
          </div>
        </div>
      </div>

      {/* Main Content Card */}
      <Card className="flex-1 bg-card/50 backdrop-blur-sm border-muted-foreground/10 shadow-xl overflow-hidden flex flex-col ring-1 ring-border/50">
        {/* Filters Header */}
        <CardHeader className="border-b bg-muted/5 py-4 px-6">
          <HistoryFiltersNew
            search={filters.search}
            onSearchChange={setSearch}
            selectedModel={filters.modelId}
            onModelChange={setModelId}
            dateRange={filters.dateRange}
            onDateRangeChange={setDateRange}
            models={models}
            activeFilterCount={activeFilterCount}
            onClearFilters={handleClearFilters}
          />
        </CardHeader>

        {/* Table Content */}
        <CardContent className="p-0 flex-1 overflow-hidden relative">
          <ScrollArea className="h-full">
            <HistoryTableNew
              history={history}
              isLoading={isLoading}
              isError={isError}
              searchQuery={filters.search}
              onClearFilters={handleClearFilters}
              onViewDetail={handleViewDetail}
            />
          </ScrollArea>
        </CardContent>

        {/* Pagination Footer */}
        <div className="border-t bg-muted/5 p-4 flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            {isLoading ? (
              <Skeleton className="h-4 w-32" />
            ) : (
              <>
                Showing page <span className="font-medium">{filters.page}</span>
                {hasActiveFilters && (
                  <span className="ml-2 text-xs">
                    (filtered)
                  </span>
                )}
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={filters.page === 1 || isLoading}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <div className="flex items-center gap-1 px-2">
              <span className="text-sm font-medium">{filters.page}</span>
            </div>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasMore || isLoading}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>

      {/* Session Detail Dialog */}
      <SessionDetailDialog
        log={selectedLog}
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
      />
    </div>
  )
}
