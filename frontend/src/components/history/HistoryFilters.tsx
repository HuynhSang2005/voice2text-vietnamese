import { Input, Select, DatePicker, Button, Flex } from 'antd'
import { SearchOutlined, FilterOutlined, ClearOutlined } from '@ant-design/icons'
import type { Dayjs } from 'dayjs'

const { RangePicker } = DatePicker

export interface HistoryFiltersValue {
  search?: string
  model?: string
  dateRange?: [Dayjs, Dayjs] | null
}

export interface HistoryFiltersProps {
  value: HistoryFiltersValue
  onChange: (value: HistoryFiltersValue) => void
  onClear: () => void
  loading?: boolean
}

const MODEL_OPTIONS = [
  { value: '', label: 'Tất cả models' },
  { value: 'zipformer', label: 'Zipformer' },
  { value: 'faster-whisper', label: 'Faster Whisper' },
  { value: 'phowhisper', label: 'PhoWhisper' },
  { value: 'hkab', label: 'HKAB' },
]

/**
 * Filters component for history list
 * Includes search input, model select, and date range picker
 * 
 * @example
 * ```tsx
 * <HistoryFilters
 *   value={filters}
 *   onChange={setFilters}
 *   onClear={handleClear}
 * />
 * ```
 */
export function HistoryFilters({
  value,
  onChange,
  onClear,
  loading = false,
}: HistoryFiltersProps) {
  const handleSearchChange = (search: string) => {
    onChange({ ...value, search })
  }

  const handleModelChange = (model: string) => {
    onChange({ ...value, model })
  }

  const handleDateRangeChange = (dateRange: [Dayjs, Dayjs] | null) => {
    onChange({ ...value, dateRange })
  }

  const hasFilters = Boolean(value.search || value.model || value.dateRange)

  return (
    <Flex wrap="wrap" gap="small" align="center">
      {/* Search Input */}
      <Input
        placeholder="Tìm kiếm nội dung..."
        prefix={<SearchOutlined />}
        value={value.search || ''}
        onChange={(e) => handleSearchChange(e.target.value)}
        allowClear
        style={{ width: 250 }}
        disabled={loading}
      />

      {/* Model Filter */}
      <Select
        placeholder="Chọn model"
        value={value.model || ''}
        onChange={handleModelChange}
        options={MODEL_OPTIONS}
        style={{ width: 180 }}
        suffixIcon={<FilterOutlined />}
        disabled={loading}
      />

      {/* Date Range Picker */}
      <RangePicker
        value={value.dateRange}
        onChange={(dates) => handleDateRangeChange(dates as [Dayjs, Dayjs] | null)}
        placeholder={['Từ ngày', 'Đến ngày']}
        format="DD/MM/YYYY"
        disabled={loading}
        allowClear
      />

      {/* Clear Filters Button */}
      {hasFilters && (
        <Button 
          icon={<ClearOutlined />} 
          onClick={onClear}
          disabled={loading}
        >
          Xóa bộ lọc
        </Button>
      )}
    </Flex>
  )
}
