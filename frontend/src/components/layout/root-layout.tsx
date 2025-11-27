/**
 * Root Layout Component
 * 
 * Main layout wrapper combining:
 * - Responsive sidebar
 * - App header with dynamic breadcrumb
 * - Main content area with proper scrolling
 */

import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import { AppSidebar } from './app-sidebar'
import { AppHeader } from './header'

interface RootLayoutProps {
  children: React.ReactNode
}

export function RootLayout({ children }: RootLayoutProps) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="flex flex-col h-screen overflow-hidden bg-background">
        <AppHeader />
        <main className="flex-1 overflow-auto">
          <div className="p-4 md:p-6 lg:p-8">
            {children}
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default RootLayout
