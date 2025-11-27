/**
 * Dynamic Breadcrumb Navigation Component
 * 
 * Automatically generates breadcrumbs based on current route
 * using TanStack Router's useRouterState hook.
 */

import { useRouterState } from '@tanstack/react-router'
import { Link } from '@tanstack/react-router'
import { Home } from 'lucide-react'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'

// Route configuration with titles and icons
interface RouteConfig {
  title: string
  icon?: React.ComponentType<{ className?: string }>
}

const routeConfig: Record<string, RouteConfig> = {
  '/': {
    title: 'Dashboard',
    icon: Home,
  },
  '/history': {
    title: 'History',
  },
}

interface BreadcrumbItem {
  path: string
  title: string
  isLast: boolean
}

export function BreadcrumbNav() {
  const pathname = useRouterState({ select: (s) => s.location.pathname })

  // Generate breadcrumb items from current path
  const breadcrumbItems = generateBreadcrumbs(pathname)

  // Don't show breadcrumb if on root with no segments
  if (breadcrumbItems.length === 0) {
    return (
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage className="text-lg font-semibold tracking-tight text-foreground/90">
              Dashboard
            </BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    )
  }

  return (
    <Breadcrumb>
      <BreadcrumbList>
        {/* Home link - always show unless on home */}
        {pathname !== '/' && (
          <>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link 
                  to="/" 
                  className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Home className="h-4 w-4" />
                  <span className="hidden sm:inline">Home</span>
                </Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
          </>
        )}

        {/* Dynamic breadcrumb items */}
        {breadcrumbItems.map((item, index) => (
          <BreadcrumbItem key={item.path}>
            {item.isLast ? (
              <BreadcrumbPage className="text-lg font-semibold tracking-tight text-foreground/90">
                {item.title}
              </BreadcrumbPage>
            ) : (
              <>
                <BreadcrumbLink asChild>
                  <Link 
                    to={item.path}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {item.title}
                  </Link>
                </BreadcrumbLink>
                {index < breadcrumbItems.length - 1 && <BreadcrumbSeparator />}
              </>
            )}
          </BreadcrumbItem>
        ))}
      </BreadcrumbList>
    </Breadcrumb>
  )
}

/**
 * Generate breadcrumb items from pathname
 */
function generateBreadcrumbs(pathname: string): BreadcrumbItem[] {
  // Handle root path
  if (pathname === '/') {
    return [{
      path: '/',
      title: routeConfig['/']?.title || 'Dashboard',
      isLast: true,
    }]
  }

  // Split path into segments
  const segments = pathname.split('/').filter(Boolean)
  
  if (segments.length === 0) {
    return []
  }

  // Build breadcrumb items
  return segments.map((segment, index) => {
    const path = '/' + segments.slice(0, index + 1).join('/')
    const config = routeConfig[path]
    const isLast = index === segments.length - 1

    // Use config title if available, otherwise capitalize segment
    const title = config?.title || capitalizeFirst(segment.replace(/-/g, ' '))

    return {
      path,
      title,
      isLast,
    }
  })
}

/**
 * Capitalize first letter of string
 */
function capitalizeFirst(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

export default BreadcrumbNav
