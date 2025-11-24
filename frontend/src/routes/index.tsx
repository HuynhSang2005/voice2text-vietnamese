import { createFileRoute } from '@tanstack/react-router'


export const Route = createFileRoute('/')({
  component: App,
})

function App() {
  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold">Voice2Text Dashboard</h1>
    </div>
  )
}

