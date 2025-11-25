import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Mic, MicOff, Activity, Clock, Wifi, WifiOff } from 'lucide-react'
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

  return (
    <div className="flex flex-col h-full p-6 gap-6">
      {/* Header Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Badge variant={isConnected ? "default" : "destructive"} className="gap-1">
            {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            {isConnected ? "Connected" : "Disconnected"}
          </Badge>
        </div>

        <div className="flex items-center gap-4">
           {latency > 0 && (
             <Badge variant="outline" className="gap-1">
               <Clock className="w-3 h-3" />
               {latency.toFixed(0)}ms
             </Badge>
           )}
        </div>
      </div>

      {/* Model Selection & Microphone Selection */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Model</CardTitle>
          </CardHeader>
          <CardContent>
            <Select value={currentModel} onValueChange={handleModelChange} disabled={isRecording}>
              {isLoadingModels ? (
                <SelectTrigger>
                  <SelectValue placeholder="Loading..." />
                </SelectTrigger>
              ) : (
                <>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {models?.map((model) => (
                      <SelectItem key={model.id} value={model.id}>
                        {model.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </>
              )}
            </Select>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Microphone</CardTitle>
          </CardHeader>
          <CardContent>
            {!hasPermission ? (
              <div className="text-sm text-muted-foreground">
                Permission required
              </div>
            ) : (
              <Select 
                value={selectedDeviceId} 
                onValueChange={setSelectedDeviceId}
                disabled={isRecording}
              >
                <SelectTrigger>
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
            )}
          </CardContent>
        </Card>
      </div>

      {/* Main Transcript Area */}
      <Card className="flex-1 flex flex-col overflow-hidden border-2">
        <CardHeader className="border-b py-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            Live Transcription
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 p-0 overflow-hidden relative">
          <ScrollArea className="h-full p-6">
            <div className="space-y-4 text-lg leading-relaxed">
              {finalText.map((text, index) => (
                <p key={index} className="text-foreground">{text}</p>
              ))}
              {partialText && (
                <p className="text-muted-foreground animate-pulse">{partialText}</p>
              )}
              {finalText.length === 0 && !partialText && (
                <div className="h-full flex items-center justify-center text-muted-foreground/50 italic">
                  Ready to transcribe...
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Bottom Controls */}
      <div className="flex flex-col items-center gap-4 pb-4">
        {/* Visualizer */}
        <div className="h-8 flex items-end gap-1">
            {isRecording && (
                <>
                    <div className="w-2 bg-primary rounded-t transition-all duration-75" style={{ height: `${Math.max(10, volume * 0.5)}%` }}></div>
                    <div className="w-2 bg-primary rounded-t transition-all duration-75" style={{ height: `${Math.max(10, volume * 0.8)}%` }}></div>
                    <div className="w-2 bg-primary rounded-t transition-all duration-75" style={{ height: `${Math.max(10, volume)}%` }}></div>
                    <div className="w-2 bg-primary rounded-t transition-all duration-75" style={{ height: `${Math.max(10, volume * 0.8)}%` }}></div>
                    <div className="w-2 bg-primary rounded-t transition-all duration-75" style={{ height: `${Math.max(10, volume * 0.5)}%` }}></div>
                </>
            )}
        </div>

        <div className="flex items-center gap-4">
            {!isRecording ? (
                <Button
                    size="lg"
                    className="h-16 w-16 rounded-full shadow-xl bg-green-600 hover:bg-green-700 transition-all hover:scale-105"
                    onClick={async () => {
                        console.log("Start button clicked")
                        // Generate new session ID
                        const sessionId = crypto.randomUUID()
                        
                        // Signal backend to start new session
                        startSession(sessionId)
                        
                        // Clear UI
                        clearTranscript()
                        
                        await startRecording()
                        setRecording(true)
                    }}
                    disabled={!isConnected}
                >
                    <Mic className="w-8 h-8" />
                </Button>
            ) : (
                <Button
                    size="lg"
                    variant="destructive"
                    className="h-16 w-16 rounded-full shadow-xl transition-all hover:scale-105"
                    onClick={() => {
                        console.log("Stop button clicked")
                        stopRecording()
                        setRecording(false)
                    }}
                >
                    <MicOff className="w-8 h-8" />
                </Button>
            )}
        </div>
        <div className="text-sm text-muted-foreground h-4">
            {isRecording ? "Listening..." : "Click mic to start"}
        </div>
      </div>
    </div>
  )
}
