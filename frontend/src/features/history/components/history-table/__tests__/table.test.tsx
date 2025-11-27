/**
 * Tests for History Table component
 * Testing: rendering, sorting, empty states, error states
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within, fireEvent } from '@testing-library/react'
import { HistoryTableNew as HistoryTable } from '../table'
import type { TranscriptionLog } from '@/client'

// Mock UI components
vi.mock('@/components/ui/table', () => ({
  Table: ({ children }: { children: React.ReactNode }) => (
    <table role="table">{children}</table>
  ),
  TableBody: ({ children }: { children: React.ReactNode }) => (
    <tbody>{children}</tbody>
  ),
  TableHead: ({ children, className }: { children?: React.ReactNode; className?: string }) => (
    <th role="columnheader" className={className}>{children}</th>
  ),
  TableHeader: ({ children, className }: { children?: React.ReactNode; className?: string }) => (
    <thead className={className}>{children}</thead>
  ),
  TableRow: ({ children, onClick, className }: { children: React.ReactNode; onClick?: () => void; className?: string }) => (
    <tr onClick={onClick} className={className} role="row">{children}</tr>
  ),
  TableCell: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <td className={className}>{children}</td>
  ),
}))

vi.mock('@/components/ui/skeleton', () => ({
  Skeleton: ({ className }: { className?: string }) => (
    <div data-testid="skeleton" className={className} />
  ),
}))

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, variant, size, asChild, ...props }: any) => {
    if (asChild) return children
    return (
      <button onClick={onClick} data-variant={variant} data-size={size} {...props}>
        {children}
      </button>
    )
  },
}))

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children, variant, className }: { children: React.ReactNode; variant?: string; className?: string }) => (
    <span data-testid="badge" data-variant={variant} className={className}>{children}</span>
  ),
}))

vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: React.ReactNode; asChild?: boolean }) => <>{children}</>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => <div data-testid="tooltip-content">{children}</div>,
}))

vi.mock('@/components/ui/dropdown-menu', () => ({
  DropdownMenu: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  DropdownMenuTrigger: ({ children }: { children: React.ReactNode; asChild?: boolean }) => <>{children}</>,
  DropdownMenuContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dropdown-content">{children}</div>
  ),
  DropdownMenuItem: ({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) => (
    <button onClick={onClick}>{children}</button>
  ),
  DropdownMenuSeparator: () => <hr />,
}))

vi.mock('lucide-react', () => ({
  FileText: () => <span data-testid="icon-file" />,
  Clock: () => <span data-testid="icon-clock" />,
  Eye: () => <span data-testid="icon-eye" />,
  Copy: () => <span data-testid="icon-copy" />,
  Trash2: () => <span data-testid="icon-trash" />,
  MoreHorizontal: () => <span data-testid="icon-more" />,
  ArrowUpDown: () => <span data-testid="icon-sort" />,
  ArrowUp: () => <span data-testid="icon-sort-up" />,
  ArrowDown: () => <span data-testid="icon-sort-down" />,
  FileSearch: () => <span data-testid="icon-search" />,
  FolderOpen: () => <span data-testid="icon-folder" />,
  Mic: () => <span data-testid="icon-mic" />,
}))

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}))

vi.mock('date-fns', () => ({
  format: (date: Date, formatStr: string) => {
    if (formatStr === 'MMM d, yyyy') return 'Jan 15, 2024'
    if (formatStr === 'HH:mm:ss') return '14:30:00'
    return date.toISOString()
  },
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

// Sample data matching TranscriptionLog type
const mockHistory: TranscriptionLog[] = [
  {
    id: 1,
    session_id: 'abc12345-6789-def0-ghij-klmnopqrstuv',
    model_id: 'zipformer',
    content: 'Đây là một bản test transcription đầu tiên.',
    latency_ms: 250,
    created_at: '2024-01-15T14:30:00Z',
  },
  {
    id: 2,
    session_id: 'xyz98765-4321-abcd-efgh-ijklmnopqrst',
    model_id: 'whisper',
    content: 'Bản ghi thứ hai với model Whisper.',
    latency_ms: 750,
    created_at: '2024-01-14T10:15:00Z',
  },
]

const mockOnViewDetail = vi.fn()
const mockOnClearFilters = vi.fn()

const defaultProps = {
  history: mockHistory,
  isLoading: false,
  isError: false,
  searchQuery: '',
  onViewDetail: mockOnViewDetail,
  onClearFilters: mockOnClearFilters,
}

describe('HistoryTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('should render table headers', () => {
      render(<HistoryTable {...defaultProps} />)

      expect(screen.getByText('Session ID')).toBeInTheDocument()
      expect(screen.getByText('Date & Time')).toBeInTheDocument()
      expect(screen.getByText('Model')).toBeInTheDocument()
      expect(screen.getByText('Transcript')).toBeInTheDocument()
      expect(screen.getByText('Latency')).toBeInTheDocument()
      expect(screen.getByText('Actions')).toBeInTheDocument()
    })

    it('should render history rows', () => {
      render(<HistoryTable {...defaultProps} />)

      // Should have 2 rows for 2 history items + 1 header row
      const rows = screen.getAllByRole('row')
      expect(rows).toHaveLength(3)
    })

    it('should display model badges with model_id values', () => {
      render(<HistoryTable {...defaultProps} />)

      const badges = screen.getAllByTestId('badge')
      expect(badges).toHaveLength(2)
      // Model IDs are displayed as-is from data (lowercase)
      expect(badges[0]).toHaveTextContent('zipformer')
      expect(badges[1]).toHaveTextContent('whisper')
    })

    it('should display session IDs truncated to 8 chars', () => {
      render(<HistoryTable {...defaultProps} />)

      expect(screen.getByText('abc12345')).toBeInTheDocument()
      expect(screen.getByText('xyz98765')).toBeInTheDocument()
    })

    it('should display transcript content', () => {
      render(<HistoryTable {...defaultProps} />)

      expect(screen.getByText(/bản test transcription/i)).toBeInTheDocument()
      expect(screen.getByText(/model Whisper/i)).toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('should show loading skeletons when isLoading is true', () => {
      render(<HistoryTable {...defaultProps} history={undefined} isLoading={true} />)

      const skeletons = screen.getAllByTestId('skeleton')
      expect(skeletons.length).toBeGreaterThan(0)
    })

    it('should show 5 skeleton rows during loading', () => {
      render(<HistoryTable {...defaultProps} history={undefined} isLoading={true} />)

      const table = screen.getByRole('table')
      const rows = within(table).getAllByRole('row')
      // 1 header row + 5 skeleton rows
      expect(rows).toHaveLength(6)
    })
  })

  describe('Empty State', () => {
    it('should show no results message when history is empty with search query', () => {
      render(<HistoryTable {...defaultProps} history={[]} searchQuery="nonexistent" />)

      expect(screen.getByText('No results found')).toBeInTheDocument()
    })

    it('should show clear filters button when onClearFilters provided and no results', () => {
      render(
        <HistoryTable
          {...defaultProps}
          history={[]}
          searchQuery="test"
          onClearFilters={mockOnClearFilters}
        />
      )

      expect(screen.getByText(/clear all filters/i)).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('should show "Unable to load history" when isError is true', () => {
      render(
        <HistoryTable
          {...defaultProps}
          history={undefined}
          isError={true}
        />
      )

      expect(screen.getByText('Unable to load history')).toBeInTheDocument()
    })
  })

  describe('Sorting', () => {
    it('should render sortable column headers with sort buttons', () => {
      render(<HistoryTable {...defaultProps} />)

      // Sortable headers should have button children
      const dateButton = screen.getByText('Date & Time').closest('button')
      const modelButton = screen.getByText('Model').closest('button')
      const latencyButton = screen.getByText('Latency').closest('button')

      expect(dateButton).toBeInTheDocument()
      expect(modelButton).toBeInTheDocument()
      expect(latencyButton).toBeInTheDocument()
    })

    it('should toggle sort direction on column click', async () => {
      render(<HistoryTable {...defaultProps} />)

      const dateButton = screen.getByText('Date & Time').closest('button')!
      fireEvent.click(dateButton)

      // Should not crash - sort state changes internally
      expect(dateButton).toBeInTheDocument()
    })
  })

  describe('Row Interaction', () => {
    it('should allow row click for selection', async () => {
      render(<HistoryTable {...defaultProps} />)

      const rows = screen.getAllByRole('row')
      // Click first data row (skip header)
      fireEvent.click(rows[1])

      // Should not crash - selection state changes internally
      expect(rows[1]).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should have proper table structure', () => {
      render(<HistoryTable {...defaultProps} />)

      expect(screen.getByRole('table')).toBeInTheDocument()
      expect(screen.getAllByRole('columnheader').length).toBeGreaterThan(0)
      expect(screen.getAllByRole('row').length).toBeGreaterThan(0)
    })
  })
})
