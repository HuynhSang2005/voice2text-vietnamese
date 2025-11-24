import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { FileText, Calendar, Clock } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

import { getHistoryOptions } from '@/client/@tanstack/react-query.gen'

export default function HistoryList() {
  const { data: history, isLoading } = useQuery({
    ...getHistoryOptions()
  })

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full p-6 gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Transcription History</h1>
        <Badge variant="secondary">{history?.length || 0} Sessions</Badge>
      </div>

      <ScrollArea className="flex-1 -mx-6 px-6">
        <div className="space-y-4 pb-6">
          {history?.map((log) => (
            <Card key={log.id} className="hover:bg-muted/50 transition-colors">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-medium flex items-center gap-2">
                    <FileText className="w-4 h-4 text-primary" />
                    Session #{log.session_id.slice(0, 8)}
                  </CardTitle>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <Badge variant="outline">{log.model_id}</Badge>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {log.created_at ? format(new Date(log.created_at), 'PP p') : 'Unknown'}
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {log.content}
                </p>
                {log.latency_ms > 0 && (
                   <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                     <Clock className="w-3 h-3" />
                     Latency: {log.latency_ms.toFixed(0)}ms
                   </div>
                )}
              </CardContent>
            </Card>
          ))}
          
          {history?.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              No history found. Start recording to create logs.
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
