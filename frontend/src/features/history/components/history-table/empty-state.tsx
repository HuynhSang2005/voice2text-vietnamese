import { FileSearch, FolderOpen, Mic } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Link } from '@tanstack/react-router'

interface EmptyStateProps {
  type: 'no-data' | 'no-results' | 'error'
  searchQuery?: string
  onClearFilters?: () => void
}

export function EmptyState({ type, searchQuery, onClearFilters }: EmptyStateProps) {
  if (type === 'error') {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4">
        <div className="p-4 rounded-full bg-destructive/10 mb-4">
          <FileSearch className="w-10 h-10 text-destructive" />
        </div>
        <h3 className="text-lg font-semibold text-foreground mb-2">
          Unable to load history
        </h3>
        <p className="text-sm text-muted-foreground text-center max-w-[300px] mb-4">
          We couldn't fetch your transcription history. Please check your connection and try again.
        </p>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Retry
        </Button>
      </div>
    )
  }

  if (type === 'no-results') {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4">
        <div className="p-4 rounded-full bg-muted mb-4">
          <FileSearch className="w-10 h-10 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold text-foreground mb-2">
          No results found
        </h3>
        <p className="text-sm text-muted-foreground text-center max-w-[300px] mb-4">
          {searchQuery 
            ? `No transcriptions match "${searchQuery}". Try adjusting your search or filters.`
            : 'No transcriptions match your current filters. Try adjusting your criteria.'
          }
        </p>
        {onClearFilters && (
          <Button variant="outline" onClick={onClearFilters}>
            Clear all filters
          </Button>
        )}
      </div>
    )
  }

  // no-data
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="p-4 rounded-full bg-primary/10 mb-4">
        <FolderOpen className="w-10 h-10 text-primary" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">
        No transcriptions yet
      </h3>
      <p className="text-sm text-muted-foreground text-center max-w-[300px] mb-4">
        Start recording your first transcription to see it appear here.
      </p>
      <Button asChild>
        <Link to="/">
          <Mic className="w-4 h-4 mr-2" />
          Start Recording
        </Link>
      </Button>
    </div>
  )
}
