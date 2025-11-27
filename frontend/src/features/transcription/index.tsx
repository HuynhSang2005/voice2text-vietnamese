/**
 * Transcription Feature
 * 
 * Main transcription page combining audio input and transcript display.
 * Rebuilt with cleaner architecture and better UX.
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Activity, Sparkles, Zap } from 'lucide-react'
// Components
import {
  RecorderButton,
  RecordingStatus,
  DeviceSelector,
  VolumeMeter,
  TranscriptList,
  TranscriptStats,
  ExportDialog,
} from './components'

// Hooks
import { useTranscription } from './hooks'

// Common components
import { ConnectionStatus } from '@/components/common'

// Model selector
import { ModelSelector } from './components'

export function TranscriptionPage() {
  const {
    // Connection
    isConnected,
    
    // Recording
    isRecording,
    volume,
    
    // Devices
    devices,
    selectedDeviceId,
    selectDevice,
    refreshDevices,
    
    // Transcription
    currentModel,
    partialText,
    transcriptLines,
    latency,
    sessionId,
    
    // Actions
    start,
    stop,
    clear,
    setModel,
  } = useTranscription()

  const handleToggleRecording = async () => {
    if (isRecording) {
      stop()
    } else {
      await start()
    }
  }

  return (
    <div className="flex flex-col h-full gap-4 max-w-6xl mx-auto">
      {/* Top Status Bar */}
      <TranscriptionHeader
        isConnected={isConnected}
        currentModel={currentModel}
        latency={latency}
        onModelChange={setModel}
      />

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 flex-1 min-h-0">
        {/* Left Panel: Controls */}
        <AudioInputPanel
          isRecording={isRecording}
          isConnected={isConnected}
          volume={volume}
          devices={devices}
          selectedDeviceId={selectedDeviceId}
          onDeviceChange={selectDevice}
          onRefreshDevices={refreshDevices}
          onToggleRecording={handleToggleRecording}
        />

        {/* Right Panel: Transcript */}
        <TranscriptPanel
          transcriptLines={transcriptLines}
          partialText={partialText}
          isRecording={isRecording}
          sessionId={sessionId}
          onClear={clear}
        />
      </div>
    </div>
  )
}

/**
 * Header with connection status and model selector
 */
interface TranscriptionHeaderProps {
  isConnected: boolean
  currentModel: string
  latency: number
  onModelChange: (model: string) => void
}

function TranscriptionHeader({
  isConnected,
  currentModel,
  latency,
  onModelChange,
}: TranscriptionHeaderProps) {
  return (
    <Card className="bg-card/50 backdrop-blur-sm border-muted-foreground/10">
      <CardContent className="py-3 px-4">
        <div className="flex items-center justify-between gap-4">
          {/* Left: Connection status */}
          <div className="flex items-center gap-3">
            <ConnectionStatus showReconnectButton={false} />
            {latency > 0 && (
              <Badge variant="secondary" className="gap-1">
                <Zap className="h-3 w-3" />
                {latency}ms
              </Badge>
            )}
          </div>

          {/* Right: Model selector */}
          <ModelSelector
            currentModel={currentModel}
            onModelChange={onModelChange}
            disabled={!isConnected}
          />
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Audio input panel with recorder and device selector
 */
interface AudioInputPanelProps {
  isRecording: boolean
  isConnected: boolean
  volume: number
  devices: Array<{ deviceId: string; label: string }>
  selectedDeviceId: string | null
  onDeviceChange: (deviceId: string) => void
  onRefreshDevices: () => Promise<void>
  onToggleRecording: () => void
}

function AudioInputPanel({
  isRecording,
  isConnected,
  volume,
  devices,
  selectedDeviceId,
  onDeviceChange,
  onRefreshDevices,
  onToggleRecording,
}: AudioInputPanelProps) {
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
        {/* Device Selector */}
        <DeviceSelector
          devices={devices}
          selectedDeviceId={selectedDeviceId}
          onDeviceChange={onDeviceChange}
          onRefresh={onRefreshDevices}
          isDisabled={isRecording}
        />

        {/* Record Button */}
        <div className="flex-1 flex flex-col items-center justify-center gap-4 py-4">
          <RecorderButton
            isRecording={isRecording}
            isConnected={isConnected}
            volume={volume}
            onToggle={onToggleRecording}
            size="lg"
          />
          <RecordingStatus isRecording={isRecording} isConnected={isConnected} />
        </div>

        {/* Volume Meter */}
        <VolumeMeter
          volume={volume}
          isActive={isRecording}
          variant="gradient"
          size="md"
        />
      </CardContent>
    </Card>
  )
}

/**
 * Transcript panel with list and export
 */
interface TranscriptPanelProps {
  transcriptLines: Array<{
    id: string
    text: string
    timestamp: number
    isFinal: boolean
    latency?: number
  }>
  partialText: string
  isRecording: boolean
  sessionId: string | null
  onClear: () => void
}

function TranscriptPanel({
  transcriptLines,
  partialText,
  isRecording,
  sessionId,
  onClear,
}: TranscriptPanelProps) {
  const hasContent = transcriptLines.length > 0 || partialText

  return (
    <Card className="lg:col-span-3 flex flex-col bg-card/50 backdrop-blur-sm border-muted-foreground/10 shadow-lg order-1 lg:order-2 h-[500px] lg:h-auto">
      <CardHeader className="border-b bg-muted/10 pb-4">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              Live Transcription
            </CardTitle>
            {hasContent && (
              <TranscriptStats lines={transcriptLines} className="mt-2" />
            )}
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={onClear}
              disabled={isRecording || transcriptLines.length === 0}
            >
              Clear
            </Button>
            <ExportDialog
              lines={transcriptLines}
              sessionId={sessionId || undefined}
              disabled={transcriptLines.length === 0}
            />
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0 relative overflow-hidden">
        <TranscriptList
          lines={transcriptLines}
          partialText={partialText}
          showTimestamp={true}
          autoScroll={true}
          emptyStateMessage="Start speaking to see transcription here..."
        />

        {/* Gradient overlay */}
        <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-card to-transparent pointer-events-none" />
      </CardContent>
    </Card>
  )
}

// Default export
export default TranscriptionPage
