import { Link, Outlet } from '@tanstack/react-router'
import { Home, History, Settings, Mic } from 'lucide-react'


export default function MainLayout() {
  return (
    <div className="flex h-screen bg-background text-foreground font-sans antialiased">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-muted/20 hidden md:flex flex-col">
        <div className="p-6 border-b">
          <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
            <Mic className="w-6 h-6 text-primary" />
            Voice2Text
          </h1>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          <NavItem to="/" icon={<Home className="w-4 h-4" />} label="Dashboard" />
          <NavItem to="/history" icon={<History className="w-4 h-4" />} label="History" />
          <NavItem to="/settings" icon={<Settings className="w-4 h-4" />} label="Settings" />
        </nav>

        <div className="p-4 border-t text-xs text-muted-foreground text-center">
          Research Dashboard v1.0
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Outlet is already rendered by the parent route wrapper in __root.tsx, 
            but MainLayout is used as a wrapper there. 
            Wait, if MainLayout is used in __root.tsx, it should render children or Outlet.
            Since MainLayout is used as a wrapper component in __root.tsx, we should use Outlet here 
            if MainLayout is part of the route hierarchy, OR children if it's just a wrapper.
            In __root.tsx: <MainLayout />. MainLayout uses <Outlet />. 
            This is correct for TanStack Router.
        */}
        <Outlet />
      </main>
    </div>
  )
}

function NavItem({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground [&.active]:bg-primary [&.active]:text-primary-foreground"
    >
      {icon}
      {label}
    </Link>
  )
}
