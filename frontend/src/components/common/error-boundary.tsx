/**
 * Error Boundary Component
 * 
 * Catches JavaScript errors in child components and displays
 * a fallback UI instead of crashing the entire application.
 */

import { Component, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertCircle, RefreshCw, Home, Bug } from 'lucide-react'
import { Link } from '@tanstack/react-router'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
  onReset?: () => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: React.ErrorInfo | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo })
    
    // Log error to console in development
    if (import.meta.env.DEV) {
      console.error('ErrorBoundary caught an error:', error)
      console.error('Component stack:', errorInfo.componentStack)
    }

    // Call optional error handler
    this.props.onError?.(error, errorInfo)
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
    this.props.onReset?.()
  }

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Default error UI
      return (
        <ErrorFallback
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onReset={this.handleReset}
        />
      )
    }

    return this.props.children
  }
}

interface ErrorFallbackProps {
  error: Error | null
  errorInfo: React.ErrorInfo | null
  onReset: () => void
}

export function ErrorFallback({ error, errorInfo, onReset }: ErrorFallbackProps) {
  const isDev = import.meta.env.DEV

  return (
    <div className="min-h-[400px] flex items-center justify-center p-6">
      <Card className="w-full max-w-lg shadow-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 p-3 rounded-full bg-destructive/10 w-fit">
            <AlertCircle className="h-8 w-8 text-destructive" />
          </div>
          <CardTitle className="text-xl">Something went wrong</CardTitle>
          <CardDescription>
            An unexpected error occurred. Don't worry, your data is safe.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Error message */}
          <div className="rounded-lg bg-muted p-4">
            <p className="text-sm font-medium text-destructive">
              {error?.message || 'Unknown error'}
            </p>
          </div>

          {/* Stack trace (dev only) */}
          {isDev && errorInfo?.componentStack && (
            <details className="text-xs">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground flex items-center gap-1">
                <Bug className="h-3 w-3" />
                Developer Info (click to expand)
              </summary>
              <pre className="mt-2 p-3 rounded bg-muted overflow-auto max-h-[200px] text-[10px] leading-relaxed">
                {error?.stack}
                {'\n\nComponent Stack:'}
                {errorInfo.componentStack}
              </pre>
            </details>
          )}
        </CardContent>

        <CardFooter className="flex flex-col sm:flex-row gap-2">
          <Button
            variant="default"
            className="w-full sm:w-auto"
            onClick={onReset}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
          <Button
            variant="outline"
            className="w-full sm:w-auto"
            asChild
          >
            <Link to="/">
              <Home className="h-4 w-4 mr-2" />
              Go Home
            </Link>
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}

/**
 * Feature Error Boundary - for wrapping feature modules
 */
export function FeatureErrorBoundary({ 
  children,
  featureName 
}: { 
  children: ReactNode
  featureName: string 
}) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        console.error(`Error in ${featureName}:`, error)
        console.error('Component stack:', errorInfo.componentStack)
      }}
    >
      {children}
    </ErrorBoundary>
  )
}

export default ErrorBoundary
