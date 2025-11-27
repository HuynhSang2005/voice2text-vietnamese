import { useState, useCallback, useEffect, useMemo, useRef } from 'react'
import type { DateRange } from 'react-day-picker'

export interface HistoryFilters {
  search: string
  modelId: string | undefined
  dateRange: DateRange | undefined
  page: number
  limit: number
}

interface UseHistoryFiltersOptions {
  defaultLimit?: number
  debounceMs?: number
}

const DEFAULT_FILTERS: HistoryFilters = {
  search: '',
  modelId: undefined,
  dateRange: undefined,
  page: 1,
  limit: 50,
}

// Custom debounce hook
function useDebouncedCallback<T extends (...args: Parameters<T>) => void>(
  callback: T,
  delay: number
): T {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const callbackRef = useRef(callback)
  
  useEffect(() => {
    callbackRef.current = callback
  }, [callback])

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  return useCallback(
    ((...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
      timeoutRef.current = setTimeout(() => {
        callbackRef.current(...args)
      }, delay)
    }) as T,
    [delay]
  )
}

export function useHistoryFilters(options: UseHistoryFiltersOptions = {}) {
  const { defaultLimit = 50, debounceMs = 300 } = options
  
  // Initialize state from defaults
  const [filters, setFiltersInternal] = useState<HistoryFilters>(() => ({
    ...DEFAULT_FILTERS,
    limit: defaultLimit,
  }))

  // Debounced search setter
  const debouncedSetSearch = useDebouncedCallback(
    (value: string) => {
      setFiltersInternal((prev) => ({ ...prev, search: value, page: 1 }))
    },
    debounceMs
  )

  // Individual setters
  const setSearch = useCallback(
    (value: string) => {
      debouncedSetSearch(value)
    },
    [debouncedSetSearch]
  )

  const setSearchImmediate = useCallback((value: string) => {
    setFiltersInternal((prev) => ({ ...prev, search: value, page: 1 }))
  }, [])

  const setModelId = useCallback((modelId: string | undefined) => {
    setFiltersInternal((prev) => ({ ...prev, modelId, page: 1 }))
  }, [])

  const setDateRange = useCallback((dateRange: DateRange | undefined) => {
    setFiltersInternal((prev) => ({ ...prev, dateRange, page: 1 }))
  }, [])

  const setPage = useCallback((page: number | ((p: number) => number)) => {
    setFiltersInternal((prev) => ({
      ...prev,
      page: typeof page === 'function' ? page(prev.page) : page,
    }))
  }, [])

  const setLimit = useCallback((limit: number) => {
    setFiltersInternal((prev) => ({ ...prev, limit, page: 1 }))
  }, [])

  // Reset all filters
  const clearFilters = useCallback(() => {
    setFiltersInternal({
      ...DEFAULT_FILTERS,
      limit: defaultLimit,
    })
  }, [defaultLimit])

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    return (
      filters.search !== '' ||
      filters.modelId !== undefined ||
      filters.dateRange !== undefined
    )
  }, [filters.search, filters.modelId, filters.dateRange])

  // Count active filters
  const activeFilterCount = useMemo(() => {
    let count = 0
    if (filters.search) count++
    if (filters.modelId) count++
    if (filters.dateRange?.from || filters.dateRange?.to) count++
    return count
  }, [filters.search, filters.modelId, filters.dateRange])

  // Convert filters to API query params
  const queryParams = useMemo(() => {
    return {
      page: filters.page,
      limit: filters.limit,
      search: filters.search || undefined,
      model: filters.modelId || undefined,
      start_date: filters.dateRange?.from?.toISOString(),
      end_date: filters.dateRange?.to?.toISOString(),
    }
  }, [filters])

  return {
    // State
    filters,
    queryParams,
    hasActiveFilters,
    activeFilterCount,

    // Individual setters
    setSearch,
    setSearchImmediate,
    setModelId,
    setDateRange,
    setPage,
    setLimit,

    // Bulk operations
    clearFilters,
    setFilters: setFiltersInternal,
  }
}
