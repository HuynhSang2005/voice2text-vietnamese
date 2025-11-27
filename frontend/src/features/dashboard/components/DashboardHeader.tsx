import { useAppStore } from '@/store/useAppStore'
import { useModelStatus } from '@/hooks/useModelStatus'
import { useQuery } from '@tanstack/react-query'
import { getModelsOptions } from '@/client/@tanstack/react-query.gen'
import { Clock, Settings2, Activity } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

export function DashboardHeader() {
    const { isConnected, latency, isRecording, currentModel } = useAppStore()
    const { isSwitchingModel, handleModelChange } = useModelStatus()

    const { data: models, isLoading: isLoadingModels } = useQuery({
        ...getModelsOptions()
    })

    return (
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
                    <Select value={currentModel} onValueChange={handleModelChange} disabled={isRecording || isLoadingModels || isSwitchingModel}>
                        <SelectTrigger className="w-full md:w-[200px] h-9 bg-background/50 border-muted-foreground/20">
                            <SelectValue placeholder={isSwitchingModel ? "Loading Model..." : "Select Model"} />
                            {isSwitchingModel && <Activity className="w-3 h-3 ml-2 animate-spin" />}
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
    )
}
