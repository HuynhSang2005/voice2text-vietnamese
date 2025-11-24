
import { useQuery } from '@tanstack/react-query'
import { Mic, MicOff, Activity, Clock, Wifi, WifiOff } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

import { useAppStore } from '@/store/useAppStore'
import { useAudioRecorder } from '@/hooks/useAudioRecorder'
import { useTranscribe } from '@/hooks/useTranscribe'
import { getModelsOptions } from '@/client/@tanstack/react-query.gen'

export default function Dashboard() {
  const { 
    isConnected, 
    isRecording, 
    currentModel, 
    partialText, 
    finalText, 
    latency,
    setModel,
    setRecording,
    clearTranscript
  } = useAppStore()

  const { sendAudio } = useTranscribe()
  const { startRecording, stopRecording } = useAudioRecorder({ 
    onAudioData: sendAudio 
  })

  // Fetch available models
  const { data: models, isLoading: isLoadingModels } = useQuery({
    ...getModelsOptions()
  })

  const handleToggleRecording = async () => {
    if (isRecording) {
      stopRecording()
      setRecording(false)
    } else {
      clearTranscript()
      await startRecording()
      setRecording(true)
    }
  }

  const handleModelChange = (value: string) => {
    setModel(value)
  }

  return (
    <div className="flex flex-col h-full p-6 gap-6">
      {/* Header Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Select value={currentModel} onValueChange={handleModelChange} disabled={isRecording}>
            <SelectTrigger className="w-[280px]">
              <SelectValue placeholder="Select Model" />
            </SelectTrigger>
            <SelectContent>
              {isLoadingModels ? (
                <div className="p-2 space-y-2">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              ) : (
                models?.map((model) => (
                  <SelectItem key={model.id} value={model.id}>
                    <div className="flex flex-col items-start">
                      <span className="font-medium">{model.name}</span>
                      <span className="text-xs text-muted-foreground">{model.description}</span>
                    </div>
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>

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
      <div className="flex justify-center pb-4">
        <Button
          size="lg"
          variant={isRecording ? "destructive" : "default"}
          className="h-16 w-16 rounded-full shadow-xl transition-all hover:scale-105"
          onClick={handleToggleRecording}
          disabled={!isConnected}
        >
          {isRecording ? (
            <MicOff className="w-8 h-8" />
          ) : (
            <Mic className="w-8 h-8" />
          )}
        </Button>
      </div>
    </div>
  )
}
