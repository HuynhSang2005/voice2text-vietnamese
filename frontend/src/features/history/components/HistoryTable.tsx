import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from '@/components/ui/badge'
import { FileText, Clock, Search } from 'lucide-react'
import { format } from 'date-fns'
import { cn } from "@/lib/utils"
import type { TranscriptionLog } from '@/client'

interface HistoryTableProps {
    history: TranscriptionLog[] | undefined
}

export function HistoryTable({ history }: HistoryTableProps) {
    return (
        <Table>
            <TableHeader className="bg-muted/30 sticky top-0 z-10 backdrop-blur-md shadow-sm">
                <TableRow className="hover:bg-transparent border-b border-border/60">
                    <TableHead className="w-[180px] pl-6">Session ID</TableHead>
                    <TableHead className="w-[200px]">Date & Time</TableHead>
                    <TableHead className="w-[180px]">Model</TableHead>
                    <TableHead>Transcript Content</TableHead>
                    <TableHead className="text-right w-[120px] pr-6">Latency</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {history?.map((log) => (
                    <TableRow key={log.id} className="group hover:bg-muted/40 transition-colors border-b border-border/40">
                        <TableCell className="font-mono text-xs text-muted-foreground pl-6">
                            <div className="flex items-center gap-2">
                                <div className="p-1.5 rounded-md bg-primary/10 text-primary">
                                    <FileText className="w-3.5 h-3.5" />
                                </div>
                                <span className="group-hover:text-foreground transition-colors">{log.session_id.slice(0, 8)}</span>
                            </div>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                            <div className="flex flex-col">
                                <span className="font-medium text-foreground">
                                    {log.created_at ? format(new Date(log.created_at), 'MMM d, yyyy') : 'Unknown'}
                                </span>
                                <span className="text-xs opacity-70">
                                    {log.created_at ? format(new Date(log.created_at), 'p') : ''}
                                </span>
                            </div>
                        </TableCell>
                        <TableCell>
                            <Badge variant="outline" className="text-[10px] font-medium bg-background/50 backdrop-blur-sm">
                                {log.model_id}
                            </Badge>
                        </TableCell>
                        <TableCell className="max-w-[500px]">
                            <p className="truncate text-sm text-foreground/90 font-medium leading-relaxed">
                                {log.content}
                            </p>
                        </TableCell>
                        <TableCell className="text-right pr-6">
                            {log.latency_ms > 0 ? (
                                <div className="flex items-center justify-end gap-1.5">
                                    <Clock className="w-3 h-3 text-muted-foreground/50" />
                                    <span className={cn("font-mono text-xs font-bold", log.latency_ms < 500 ? "text-green-500" : "text-yellow-500")}>
                                        {log.latency_ms.toFixed(0)}ms
                                    </span>
                                </div>
                            ) : (
                                <span className="text-muted-foreground">-</span>
                            )}
                        </TableCell>
                    </TableRow>
                ))}
                {history?.length === 0 && (
                    <TableRow>
                        <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                            <div className="flex flex-col items-center justify-center gap-2">
                                <Search className="w-8 h-8 opacity-20" />
                                <p>No history found matching your filters.</p>
                            </div>
                        </TableCell>
                    </TableRow>
                )}
            </TableBody>
        </Table>
    )
}
