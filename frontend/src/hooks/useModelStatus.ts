import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getModelStatusOptions } from '@/client/@tanstack/react-query.gen'
import { useAppStore } from '@/store/useAppStore'

// Type for model status response (should match backend)
interface ModelStatusResponse {
    status: 'ready' | 'loading' | 'error'
    current_model: string | null
    message?: string
}

export const useModelStatus = () => {
    const { currentModel, setModel } = useAppStore()
    const [isSwitchingModel, setIsSwitchingModel] = useState(false)

    // Poll model status
    const { data } = useQuery({
        ...getModelStatusOptions(),
        refetchInterval: 1000, // Poll every 1s
    })

    // Type assertion since backend returns unknown type
    const modelStatus = data as ModelStatusResponse | undefined

    // Sync local state with backend status
    useEffect(() => {
        if (modelStatus?.status === 'ready' && modelStatus.current_model === currentModel) {
            setIsSwitchingModel(false)
        } else if (modelStatus?.status === 'loading' || (modelStatus?.current_model && modelStatus.current_model !== currentModel)) {
            setIsSwitchingModel(true)
        }
    }, [modelStatus, currentModel])

    const handleModelChange = (value: string) => {
        setIsSwitchingModel(true)
        setModel(value)
    }

    return {
        modelStatus,
        isSwitchingModel,
        handleModelChange
    }
}
