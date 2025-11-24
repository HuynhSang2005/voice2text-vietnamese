import { createFileRoute } from '@tanstack/react-router'
import HistoryList from '@/features/history/HistoryList'

export const Route = createFileRoute('/history')({
  component: HistoryList,
})
