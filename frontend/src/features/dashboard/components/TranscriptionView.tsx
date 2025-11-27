import { useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Sparkles, Mic } from 'lucide-react'

interface TranscriptionViewProps {
    finalText: string[]
    partialText: string
    isRecording: boolean
    onClear: () => void
}

export function TranscriptionView({ finalText, partialText, isRecording, onClear }: TranscriptionViewProps) {
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
        <Card className="lg:col-span-3 flex flex-col bg-card/50 backdrop-blur-sm border-muted-foreground/10 shadow-lg order-1 lg:order-2 h-[500px] lg:h-auto">
            <CardHeader className="border-b bg-muted/10 pb-4">
                <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-primary" />
                        Live Transcription
                    </CardTitle>
                    <div className="flex gap-2">
                        <Button variant="ghost" size="sm" onClick={onClear} disabled={isRecording || finalText.length === 0}>
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
    )
}
