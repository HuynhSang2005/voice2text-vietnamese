import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface HistoryPaginationProps {
    page: number
    setPage: (page: number | ((p: number) => number)) => void
    hasMore: boolean
}

export function HistoryPagination({ page, setPage, hasMore }: HistoryPaginationProps) {
    return (
        <div className="border-t bg-muted/5 p-4 flex items-center justify-between">
            <div className="text-xs text-muted-foreground">
                Showing page {page}
            </div>
            <div className="flex items-center gap-2">
                <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                >
                    <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setPage(p => p + 1)}
                    disabled={!hasMore}
                >
                    <ChevronRight className="h-4 w-4" />
                </Button>
            </div>
        </div>
    )
}
