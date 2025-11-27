/**
 * App Sidebar Component
 * 
 * Responsive sidebar with:
 * - Collapsed mode for mobile
 * - localStorage persistence for collapsed state
 * - Keyboard shortcuts support (Cmd/Ctrl + B)
 * - Active route highlighting
 */

import { useEffect, useCallback } from 'react'
import { Home, History, Mic, Keyboard } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar"
import { Link, useLocation } from "@tanstack/react-router"
import { Badge } from "@/components/ui/badge"
import { 
  Tooltip, 
  TooltipContent, 
  TooltipProvider, 
  TooltipTrigger 
} from "@/components/ui/tooltip"

// Menu items with icons and metadata
const navigationItems = [
  {
    title: "Dashboard",
    url: "/",
    icon: Home,
    description: "Real-time transcription",
  },
  {
    title: "History",
    url: "/history",
    icon: History,
    description: "View past sessions",
  },
]

// Storage key for sidebar state
const SIDEBAR_STATE_KEY = 'sidebar-collapsed'

export function AppSidebar() {
  const location = useLocation()
  const { state, setOpen, toggleSidebar, isMobile } = useSidebar()

  // Restore sidebar state from localStorage on mount (only once)
  useEffect(() => {
    if (isMobile) return // Don't persist state on mobile
    
    const savedState = localStorage.getItem(SIDEBAR_STATE_KEY)
    if (savedState !== null) {
      const isCollapsed = savedState === 'true'
      setOpen(!isCollapsed)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Empty deps - only run on mount

  // Save sidebar state to localStorage when it changes (skip initial render)
  useEffect(() => {
    if (isMobile) return // Don't persist state on mobile
    
    // Only save after initial mount
    const isCollapsed = state === 'collapsed'
    localStorage.setItem(SIDEBAR_STATE_KEY, String(isCollapsed))
  }, [state, isMobile])

  // Keyboard shortcut handler (Cmd/Ctrl + B)
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'b') {
      event.preventDefault()
      toggleSidebar()
    }
  }, [toggleSidebar])

  // Register keyboard shortcut
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <Sidebar collapsible="icon" className="border-r bg-sidebar">
      {/* Header with Logo */}
      <SidebarHeader className="h-16 flex items-center justify-center border-b bg-sidebar-accent/30">
        <div className="flex items-center gap-2.5 font-bold text-xl text-primary">
          <Mic className="h-6 w-6 shrink-0" />
          <span className="group-data-[collapsible=icon]:hidden whitespace-nowrap">
            Voice2Text
          </span>
        </div>
      </SidebarHeader>

      {/* Main Navigation */}
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-xs uppercase tracking-wider text-muted-foreground/70">
            Navigation
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navigationItems.map((item) => {
                const isActive = location.pathname === item.url
                
                return (
                  <SidebarMenuItem key={item.title}>
                    <TooltipProvider delayDuration={0}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <SidebarMenuButton 
                            asChild 
                            isActive={isActive}
                            className="transition-all duration-200"
                          >
                            <Link to={item.url}>
                              <item.icon className="shrink-0" />
                              <span>{item.title}</span>
                              {isActive && (
                                <Badge 
                                  variant="secondary" 
                                  className="ml-auto h-5 px-1.5 text-[10px] group-data-[collapsible=icon]:hidden"
                                >
                                  Active
                                </Badge>
                              )}
                            </Link>
                          </SidebarMenuButton>
                        </TooltipTrigger>
                        <TooltipContent 
                          side="right" 
                          className="group-data-[collapsible=expanded]:hidden"
                        >
                          <p className="font-medium">{item.title}</p>
                          <p className="text-xs text-muted-foreground">
                            {item.description}
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {/* Footer with keyboard shortcut hint */}
      <SidebarFooter className="border-t">
        <div className="p-2 group-data-[collapsible=icon]:hidden">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Keyboard className="h-3.5 w-3.5" />
            <span>
              <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">
                {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}
              </kbd>
              {' + '}
              <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">
                B
              </kbd>
              {' to toggle'}
            </span>
          </div>
        </div>
      </SidebarFooter>
      
      <SidebarRail />
    </Sidebar>
  )
}
