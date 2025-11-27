import { useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Mic, MicOff, Activity, Clock, Wifi, WifiOff, Settings2, Sparkles } from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'
import { useTranscribe } from '@/hooks/useTranscribe'
import { useAudioRecorder } from '@/hooks/useAudioRecorder'
import { useMicrophoneDevices } from '@/hooks/useMicrophoneDevices'
import { useQuery } from '@tanstack/react-query'
import { getModelsOptions } from '@/client/@tanstack/react-query.gen'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

export default function Dashboard() {
  const {
    isConnected,
    isRecording,
    currentModel,
    partialText,
    finalText,
    latency,
    setRecording,
    setModel,
    clearTranscript
  } = useAppStore()

  const { sendAudio, startSession } = useTranscribe()
  const { devices, selectedDeviceId, setSelectedDeviceId, hasPermission } = useMicrophoneDevices()
  const { startRecording, stopRecording, volume } = useAudioRecorder({ 
    onAudioData: sendAudio,
    deviceId: selectedDeviceId
  })

  // Fetch available models
  const { data: models, isLoading: isLoadingModels } = useQuery({
    ...getModelsOptions()
  })

  const handleModelChange = (value: string) => {
    setModel(value)
  }

  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
        const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
        if (scrollContainer) {
            scrollContainer.scrollTop = scrollContainer.scrollHeight;
        }
    }
  }, [finalText, partialText])


  return (
    <div className="flex flex-col h-full gap-4 max-w-6xl mx-auto">
      {/* Top Status Bar */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-card/50 p-4 rounded-xl border backdrop-blur-sm shadow-sm">
        <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
                <div className={cn("w-3 h-3 rounded-full animate-pulse", isConnected ? "bg-green-500" : "bg-red-500")} />
                <span className="text-sm font-medium text-muted-foreground">
                    {isConnected ? "System Ready" : "Disconnected"}
                </span>
            </div>
            <Separator orientation="vertical" className="h-4" />
             {latency > 0 && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="w-4 h-4" />
                <span className={cn("font-mono font-bold", latency < 500 ? "text-green-500" : "text-yellow-500")}>
                    {latency.toFixed(0)}ms
                </span>
                <span className="text-xs text-muted-foreground/50">latency</span>
              </div>
           )}
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
             <div className="flex items-center gap-2 flex-1 md:flex-none">
                <Settings2 className="w-4 h-4 text-muted-foreground" />
                <Select value={currentModel} onValueChange={handleModelChange} disabled={isRecording || isLoadingModels}>
                  <SelectTrigger className="w-full md:w-[200px] h-9 bg-background/50 border-muted-foreground/20">
                    <SelectValue placeholder="Select Model" />
                  </SelectTrigger>
                  <SelectContent className="bg-popover/95 backdrop-blur-xl border-border/50 shadow-xl">
                    {models?.map((model) => (
                      <SelectItem key={model.id} value={model.id}>
                        <div className="flex items-center justify-between w-full gap-2">
                            <span>{model.name}</span>
                            {model.id.includes('zipformer') && <Badge variant="secondary" className="text-[10px] h-4 px-1">Fast</Badge>}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
            </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 flex-1 min-h-0">
        
        {/* Left Panel: Controls & Visualizer */}
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
                            onClick={async () => {
                                if (isRecording) {
                                    stopRecording()
                                    setRecording(false)
                                } else {
                                    const sessionId = crypto.randomUUID()
                                    startSession(sessionId)
                                    clearTranscript()
                                    await startRecording()
                                    setRecording(true)
                                }
                            }}
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

        {/* Right Panel: Transcript */}
        <Card className="lg:col-span-3 flex flex-col bg-card/50 backdrop-blur-sm border-muted-foreground/10 shadow-lg order-1 lg:order-2 h-[500px] lg:h-auto">
            <CardHeader className="border-b bg-muted/10 pb-4">
                <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-primary" />
                        Live Transcription
                    </CardTitle>
                    <div className="flex gap-2">
                        <Button variant="ghost" size="sm" onClick={clearTranscript} disabled={isRecording || finalText.length === 0}>
                            Clear
                        </Button>
                        <Button variant="outline" size="sm" className="gap-2">
                            Export
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="flex-1 p-0 relative overflow-hidden">
                <ScrollArea className="h-full p-6" ref={scrollRef}>
                    <div className="space-y-6 max-w-3xl mx-auto">
                        {finalText.length === 0 && !partialText && (
                            <div className="flex flex-col items-center justify-center h-[300px] text-muted-foreground/40 gap-4">
                                <Mic className="w-12 h-12 opacity-20" />
                                <p className="text-lg font-medium">Start speaking to see text here...</p>
                            </div>
                        )}
                        
                        {finalText.map((text, index) => (
                            <div key={index} className="group relative pl-4 border-l-2 border-primary/20 hover:border-primary transition-colors">
                                <p className="text-lg leading-relaxed text-foreground/90">{text}</p>
                                <span className="absolute -left-[5px] top-0 w-2 h-2 rounded-full bg-primary/20 group-hover:bg-primary transition-colors opacity-0 group-hover:opacity-100" />
                            </div>
                        ))}
                        
                        {partialText && (
                            <div className="pl-4 border-l-2 border-primary animate-pulse">
                                <p className="text-lg leading-relaxed text-muted-foreground italic">{partialText}</p>
                            </div>
                        )}
                        {/* Spacer for auto-scroll */}
                        <div className="h-10" />
                    </div>
                </ScrollArea>
                
                {/* Gradient Overlay for bottom fade */}
                <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-background to-transparent pointer-events-none" />
            </CardContent>
        </Card>

      </div>
    </div>
  )
}
