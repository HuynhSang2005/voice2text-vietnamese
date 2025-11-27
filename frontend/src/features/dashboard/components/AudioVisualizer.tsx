import { Button } from '@/components/ui/button'
import { Mic, MicOff } from 'lucide-react'
import { cn } from "@/lib/utils"

interface AudioVisualizerProps {
    isRecording: boolean
    volume: number
    isConnected: boolean
    onToggleRecording: () => void
}

export function AudioVisualizer({ isRecording, volume, isConnected, onToggleRecording }: AudioVisualizerProps) {
    return (
        <div className="flex-1 flex flex-col items-center justify-center gap-6 py-8">
            {/* Visualizer Circle */}
            <div className="relative flex items-center justify-center">
                {isRecording && (
                    <>
                        <div className="absolute inset-0 rounded-full bg-primary/20 animate-ping" style={{ transform: `scale(${1 + volume * 0.02})` }} />
                        <div className="absolute inset-0 rounded-full bg-primary/10 animate-pulse delay-75" style={{ transform: `scale(${1 + volume * 0.04})` }} />
                    </>
                )}
                <Button
                    size="lg"
                    className={cn(
                        "h-24 w-24 rounded-full shadow-2xl transition-all duration-300 border-4",
                        isRecording
                            ? "bg-destructive hover:bg-destructive/90 border-destructive/30 hover:scale-105"
                            : "bg-primary hover:bg-primary/90 border-primary/30 hover:scale-105"
                    )}
                    onClick={onToggleRecording}
                    disabled={!isConnected}
                >
                    {isRecording ? <MicOff className="w-10 h-10" /> : <Mic className="w-10 h-10 text-primary-foreground" />}
                </Button>
            </div>

            <div className="text-center space-y-1">
                <h3 className={cn("font-semibold text-lg transition-colors", isRecording ? "text-destructive" : "text-foreground")}>
                    {isRecording ? "Recording..." : "Ready to Record"}
                </h3>
                <p className="text-xs text-muted-foreground">
                    {isRecording ? "Listening to audio stream" : "Click microphone to start"}
                </p>
            </div>
        </div>
    )
}
