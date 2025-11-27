import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { FileText, Calendar, Clock, Search, Filter } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

import { getHistoryOptions } from '@/client/@tanstack/react-query.gen'

export default function HistoryList() {
  const { data: history, isLoading } = useQuery({
    ...getHistoryOptions()
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
    <div className="flex flex-col h-full gap-6 max-w-6xl mx-auto">
      
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
            <h1 className="text-3xl font-bold tracking-tight">Transcription History</h1>
            <p className="text-muted-foreground mt-1">Review your past sessions and performance metrics.</p>
        </div>
        <div className="flex items-center gap-2">
            <Badge variant="secondary" className="h-8 px-3 text-sm">
                {history?.length || 0} Sessions
            </Badge>
            <Button variant="outline" size="sm" className="h-8 gap-2">
                <Filter className="w-3 h-3" />
                Filter
            </Button>
        </div>
      </div>

      <Card className="flex-1 bg-card/50 backdrop-blur-sm border-muted-foreground/10 shadow-lg overflow-hidden flex flex-col">
        <CardHeader className="border-b bg-muted/10 py-4">
            <div className="flex items-center gap-4">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        type="search"
                        placeholder="Search transcripts..."
                        className="pl-9 bg-background/50 border-muted-foreground/20"
                    />
                </div>
            </div>
        </CardHeader>
        <CardContent className="p-0 flex-1 overflow-hidden">
            <ScrollArea className="h-full">
                <Table>
                    <TableHeader className="bg-muted/20 sticky top-0 z-10 backdrop-blur-md">
                        <TableRow className="hover:bg-transparent">
                            <TableHead className="w-[180px]">Session ID</TableHead>
                            <TableHead className="w-[150px]">Date & Time</TableHead>
                            <TableHead className="w-[120px]">Model</TableHead>
                            <TableHead>Transcript Content</TableHead>
                            <TableHead className="text-right w-[100px]">Latency</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {history?.map((log) => (
                            <TableRow key={log.id} className="group hover:bg-muted/30 transition-colors">
                                <TableCell className="font-mono text-xs text-muted-foreground">
                                    <div className="flex items-center gap-2">
                                        <FileText className="w-3 h-3 text-primary" />
                                        {log.session_id.slice(0, 8)}
                                    </div>
                                </TableCell>
                                <TableCell className="text-xs text-muted-foreground">
                                    <div className="flex flex-col">
                                        <span className="font-medium text-foreground">
                                            {log.created_at ? format(new Date(log.created_at), 'MMM d, yyyy') : 'Unknown'}
                                        </span>
                                        <span>
                                            {log.created_at ? format(new Date(log.created_at), 'p') : ''}
                                        </span>
                                    </div>
                                </TableCell>
                                <TableCell>
                                    <Badge variant="outline" className="text-[10px] font-normal">
                                        {log.model_id}
                                    </Badge>
                                </TableCell>
                                <TableCell className="max-w-[400px]">
                                    <p className="truncate text-sm text-foreground/90 font-medium">
                                        {log.content}
                                    </p>
                                </TableCell>
                                <TableCell className="text-right">
                                    {log.latency_ms > 0 ? (
                                        <span className={cn("font-mono text-xs font-bold", log.latency_ms < 500 ? "text-green-500" : "text-yellow-500")}>
                                            {log.latency_ms.toFixed(0)}ms
                                        </span>
                                    ) : (
                                        <span className="text-muted-foreground">-</span>
                                    )}
                                </TableCell>
                            </TableRow>
                        ))}
                        {history?.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                                    No history found.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}
