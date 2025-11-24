import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Settings as SettingsIcon } from 'lucide-react'

export const Route = createFileRoute('/settings')({
  component: Settings,
})

function Settings() {
  return (
    <div className="flex flex-col h-full p-6 gap-6">
      <div className="flex items-center gap-2">
        <SettingsIcon className="w-6 h-6" />
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>General Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="auto-scroll">Auto-scroll Transcript</Label>
            <Switch id="auto-scroll" defaultChecked />
          </div>
          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="notifications">Enable Notifications</Label>
            <Switch id="notifications" defaultChecked />
          </div>
        </CardContent>
      </Card>
      
      <div className="text-sm text-muted-foreground">
        More settings coming soon...
      </div>
    </div>
  )
}
