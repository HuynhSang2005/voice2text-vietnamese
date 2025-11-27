import { useState } from 'react'
import { Search, Filter, Check, CalendarIcon, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Calendar } from '@/components/ui/calendar'
import { cn } from '@/lib/utils'
import { format, addDays } from 'date-fns'
import type { DateRange } from 'react-day-picker'

interface HistoryFiltersNewProps {
  search: string
  onSearchChange: (value: string) => void
  selectedModel: string | undefined
  onModelChange: (value: string | undefined) => void
  dateRange: DateRange | undefined
  onDateRangeChange: (range: DateRange | undefined) => void
  models: { id: string; name: string }[] | undefined
  activeFilterCount: number
  onClearFilters: () => void
}

export function HistoryFiltersNew({
  search,
  onSearchChange,
  selectedModel,
  onModelChange,
  dateRange,
  onDateRangeChange,
  models,
  activeFilterCount,
  onClearFilters,
}: HistoryFiltersNewProps) {
  const [searchValue, setSearchValue] = useState(search)

  const handleSearchChange = (value: string) => {
    setSearchValue(value)
    onSearchChange(value)
  }

  // Quick date range presets
  const datePresets = [
    { label: 'Today', range: { from: new Date(), to: new Date() } },
    { label: 'Last 7 days', range: { from: addDays(new Date(), -7), to: new Date() } },
    { label: 'Last 30 days', range: { from: addDays(new Date(), -30), to: new Date() } },
    { label: 'Last 90 days', range: { from: addDays(new Date(), -90), to: new Date() } },
  ]

  return (
    <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
      {/* Search Input */}
      <div className="relative flex-1 w-full md:max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search transcripts..."
          className="pl-9 pr-9 bg-background/50 border-muted-foreground/20 h-9"
          value={searchValue}
          onChange={(e) => handleSearchChange(e.target.value)}
        />
        {searchValue && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
            onClick={() => handleSearchChange('')}
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>

      {/* Filter Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Model Filter */}
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className={cn(
                'h-9 gap-2 border-dashed',
                selectedModel && 'border-primary/50 bg-primary/5'
              )}
            >
              <Filter className="w-3.5 h-3.5" />
              {selectedModel
                ? models?.find((m) => m.id === selectedModel)?.name || selectedModel
                : 'Model'}
              {selectedModel && (
                <Badge
                  variant="secondary"
                  className="h-4 w-4 p-0 flex items-center justify-center rounded-full"
                >
                  1
                </Badge>
              )}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="p-0 w-[200px]" align="end">
            <Command>
              <CommandInput placeholder="Search model..." />
              <CommandList>
                <CommandEmpty>No model found.</CommandEmpty>
                <CommandGroup>
                  <CommandItem
                    value="all"
                    onSelect={() => onModelChange(undefined)}
                  >
                    <Check
                      className={cn(
                        'mr-2 h-4 w-4',
                        !selectedModel ? 'opacity-100' : 'opacity-0'
                      )}
                    />
                    All Models
                  </CommandItem>
                  {models?.map((model) => (
                    <CommandItem
                      key={model.id}
                      value={model.id}
                      onSelect={(value) => {
                        onModelChange(value === selectedModel ? undefined : value)
                      }}
                    >
                      <Check
                        className={cn(
                          'mr-2 h-4 w-4',
                          selectedModel === model.id ? 'opacity-100' : 'opacity-0'
                        )}
                      />
                      {model.name}
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>

        {/* Date Range Filter */}
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className={cn(
                'h-9 gap-2 justify-start text-left font-normal min-w-[200px]',
                !dateRange && 'text-muted-foreground',
                dateRange && 'border-primary/50 bg-primary/5'
              )}
            >
              <CalendarIcon className="h-4 w-4" />
              {dateRange?.from ? (
                dateRange.to ? (
                  <>
                    {format(dateRange.from, 'MMM d')} - {format(dateRange.to, 'MMM d, yyyy')}
                  </>
                ) : (
                  format(dateRange.from, 'MMM d, yyyy')
                )
              ) : (
                <span>Date range</span>
              )}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="end">
            <div className="p-3 border-b">
              <div className="flex flex-wrap gap-1">
                {datePresets.map((preset) => (
                  <Button
                    key={preset.label}
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => onDateRangeChange(preset.range)}
                  >
                    {preset.label}
                  </Button>
                ))}
                {dateRange && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-destructive"
                    onClick={() => onDateRangeChange(undefined)}
                  >
                    Clear
                  </Button>
                )}
              </div>
            </div>
            <Calendar
              initialFocus
              mode="range"
              defaultMonth={dateRange?.from}
              selected={dateRange}
              onSelect={onDateRangeChange}
              numberOfMonths={2}
            />
          </PopoverContent>
        </Popover>

        {/* Clear All Filters */}
        {activeFilterCount > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="h-9 px-2 text-muted-foreground hover:text-foreground"
            onClick={onClearFilters}
          >
            <X className="h-3.5 w-3.5 mr-1" />
            Clear ({activeFilterCount})
          </Button>
        )}
      </div>
    </div>
  )
}
