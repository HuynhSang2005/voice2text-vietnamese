import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { AppSidebar } from '@/components/layout/app-sidebar'
import { Separator } from '@/components/ui/separator'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from '@/components/ui/breadcrumb'

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="flex flex-col w-full h-screen overflow-hidden bg-background text-foreground transition-colors duration-300">
        <header className="flex h-20 shrink-0 items-center gap-4 border-b px-6 bg-background/80 backdrop-blur-xl sticky top-0 z-10 shadow-sm">
          <SidebarTrigger className="-ml-2 h-10 w-10 hover:bg-accent/50 transition-colors" />
          <Separator orientation="vertical" className="mr-2 h-6 bg-border/50" />
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbPage className="text-lg font-semibold tracking-tight text-foreground/90">Dashboard</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </header>
        <div className="flex-1 overflow-auto p-4 md:p-6 lg:p-8 relative">
          {children}
        </div>
      </main>
    </SidebarProvider>
  )
}
