/**
 * App Header Component
 * 
 * Main header with sidebar trigger, breadcrumb navigation,
 * and connection status indicator.
 */

import { SidebarTrigger } from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import { BreadcrumbNav } from './breadcrumb-nav'
import { ConnectionStatus } from '@/components/common/connection-status'

export function AppHeader() {
  return (
    <header className="flex h-16 shrink-0 items-center gap-4 border-b px-4 md:px-6 bg-background/80 backdrop-blur-xl sticky top-0 z-10 shadow-sm">
      {/* Sidebar Toggle */}
      <SidebarTrigger className="-ml-1 h-9 w-9 hover:bg-accent/50 transition-colors" />
      
      <Separator orientation="vertical" className="h-5 bg-border/50" />
      
      {/* Dynamic Breadcrumb */}
      <div className="flex-1 min-w-0">
        <BreadcrumbNav />
      </div>

      {/* Right side: Connection Status */}
      <div className="flex items-center gap-3 ml-auto">
        <ConnectionStatus />
      </div>
    </header>
  )
}

export default AppHeader
