import { useAppStore } from '@/store/useAppStore'
import { useTranscribe } from '@/hooks/useTranscribe'
import { useAudioRecorder } from '@/hooks/useAudioRecorder'
import { useMicrophoneDevices } from '@/hooks/useMicrophoneDevices'
import { DashboardHeader } from './components/DashboardHeader'
import { AudioControlPanel } from './components/AudioControlPanel'
import { TranscriptionView } from './components/TranscriptionView'

export default function Dashboard() {
  const {
    isConnected,
    isRecording,
    partialText,
    finalText,
    setRecording,
    clearTranscript
  } = useAppStore()

  const { sendAudio, startSession } = useTranscribe()
  const { devices, selectedDeviceId, setSelectedDeviceId } = useMicrophoneDevices()
  const { startRecording, stopRecording, volume } = useAudioRecorder({ 
    onAudioData: sendAudio,
    deviceId: selectedDeviceId
  })

  const handleToggleRecording = async () => {
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
  }

  return (
    <div className="flex flex-col h-full gap-4 max-w-6xl mx-auto">
      {/* Top Status Bar */}
      <DashboardHeader />

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 flex-1 min-h-0">
        
        {/* Left Panel: Controls & Visualizer */}
        <AudioControlPanel 
            isRecording={isRecording}
            volume={volume}
            isConnected={isConnected}
            devices={devices}
            selectedDeviceId={selectedDeviceId}
            setSelectedDeviceId={setSelectedDeviceId}
            onToggleRecording={handleToggleRecording}
        />

        {/* Right Panel: Transcript */}
        <TranscriptionView 
            finalText={finalText}
            partialText={partialText}
            isRecording={isRecording}
            onClear={clearTranscript}
        />

      </div>
    </div>
  )
}
