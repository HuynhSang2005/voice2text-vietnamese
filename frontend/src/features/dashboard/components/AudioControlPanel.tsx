import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Activity } from 'lucide-react'
import { AudioVisualizer } from './AudioVisualizer'
import type { MicrophoneDevice } from '@/hooks/useMicrophoneDevices'
import { cn } from "@/lib/utils"

interface AudioControlPanelProps {
    isRecording: boolean
    volume: number
    isConnected: boolean
    devices: MicrophoneDevice[]
    selectedDeviceId: string
    setSelectedDeviceId: (id: string) => void
    onToggleRecording: () => void
}

export function AudioControlPanel({
    isRecording,
    volume,
    isConnected,
    devices,
    selectedDeviceId,
    setSelectedDeviceId,
    onToggleRecording
}: AudioControlPanelProps) {
    return (
        <Card className="lg:col-span-1 flex flex-col bg-card/50 backdrop-blur-sm border-muted-foreground/10 shadow-lg order-2 lg:order-1">
            <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                    <Activity className="w-5 h-5 text-primary" />
                    Audio Input
                </CardTitle>
                <CardDescription>Microphone settings & status</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col gap-6">

                <div className="space-y-2">
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Device</label>
                    <Select
                        value={selectedDeviceId}
                        onValueChange={setSelectedDeviceId}
                        disabled={isRecording}
                    >
                        <SelectTrigger className="w-full bg-background/50">
                            <SelectValue placeholder="Select microphone" />
                        </SelectTrigger>
                        <SelectContent>
                            {devices.map((device) => (
                                <SelectItem key={device.deviceId} value={device.deviceId}>
                                    {device.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                <AudioVisualizer
                    isRecording={isRecording}
                    volume={volume}
                    isConnected={isConnected}
                    onToggleRecording={onToggleRecording}
                />

                {/* Volume Bar */}
                <div className="space-y-2">
                    <div className="flex justify-between text-xs text-muted-foreground">
                        <span>Input Level</span>
                        <span>{Math.round(volume)}%</span>
                    </div>
                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                        <div
                            className={cn("h-full transition-all duration-75 ease-out", isRecording ? "bg-primary" : "bg-muted-foreground/30")}
                            style={{ width: `${Math.min(100, volume)}%` }}
                        />
                    </div>
                </div>

            </CardContent>
        </Card>
    )
}
