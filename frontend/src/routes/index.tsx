import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: HomePage,
})

function HomePage() {
  return (
    <main className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold text-center text-gray-900">
        Voice to Text
      </h1>
      <p className="text-center text-gray-600 mt-4">
        Vietnamese Speech Recognition
      </p>
    </main>
  )
}
