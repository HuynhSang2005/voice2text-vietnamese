import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { getHistoryOptions, getModelsOptions } from '@/client/@tanstack/react-query.gen'
import { HistoryFilters } from './components/HistoryFilters'
import { HistoryTable } from './components/HistoryTable'
import { HistoryPagination } from './components/HistoryPagination'

export default function HistoryList() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedModel, setSelectedModel] = useState<string | undefined>()
  const [date, setDate] = useState<Date | undefined>()

  const { data: history, isLoading } = useQuery({
    ...getHistoryOptions({
        query: {
            page,
            limit: 50,
            search: search || undefined,
            model: selectedModel || undefined,
            // start_date: date ? date.toISOString() : undefined // Simple date filter for now
        }
    })
  })

  const { data: models } = useQuery({
    ...getModelsOptions()
  })

  if (isLoading) {
    return (
      <div className="p-6 space-y-4 max-w-6xl mx-auto">
        <div className="flex items-center justify-between">
             <Skeleton className="h-8 w-48" />
             <Skeleton className="h-8 w-24" />
        </div>
        <Skeleton className="h-[400px] w-full rounded-xl" />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full gap-6 max-w-[1600px] mx-auto p-6">
      
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
            <h1 className="text-4xl font-bold tracking-tight text-foreground">Transcription History</h1>
            <p className="text-muted-foreground mt-2 text-lg">Review your past sessions and performance metrics.</p>
        </div>
        <div className="flex items-center gap-3">
             <div className="flex items-center gap-2 bg-card border rounded-md px-3 py-1 shadow-sm">
                <span className="text-sm font-medium text-muted-foreground">Total Sessions:</span>
                <Badge variant="secondary" className="h-6 px-2 text-xs font-bold">
                    {history?.length || 0}
                </Badge>
             </div>
        </div>
      </div>

      <Card className="flex-1 bg-card/50 backdrop-blur-sm border-muted-foreground/10 shadow-xl overflow-hidden flex flex-col ring-1 ring-border/50">
        <CardHeader className="border-b bg-muted/5 py-4 px-6">
            <HistoryFilters 
                search={search}
                setSearch={setSearch}
                selectedModel={selectedModel}
                setSelectedModel={setSelectedModel}
                date={date}
                setDate={setDate}
                models={models}
            />
        </CardHeader>
        <CardContent className="p-0 flex-1 overflow-hidden relative">
            <ScrollArea className="h-full">
                <HistoryTable history={history} />
            </ScrollArea>
        </CardContent>
        
        <HistoryPagination 
            page={page}
            setPage={setPage}
            hasMore={!!history && history.length >= 50}
        />
      </Card>
    </div>
  )
}
