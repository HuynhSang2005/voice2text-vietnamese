import { Search, Filter, Check, Calendar as CalendarIcon } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Calendar } from "@/components/ui/calendar"
import { cn } from "@/lib/utils"
import { format } from 'date-fns'

interface HistoryFiltersProps {
    search: string
    setSearch: (value: string) => void
    selectedModel: string | undefined
    setSelectedModel: (value: string | undefined) => void
    date: Date | undefined
    setDate: (date: Date | undefined) => void
    models: { id: string; name: string }[] | undefined
}

export function HistoryFilters({
    search,
    setSearch,
    selectedModel,
    setSelectedModel,
    date,
    setDate,
    models
}: HistoryFiltersProps) {
    return (
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="relative flex-1 w-full md:max-w-md">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                    type="search"
                    placeholder="Search transcripts..."
                    className="pl-9 bg-background/50 border-muted-foreground/20 h-9 transition-all focus:w-full md:focus:w-[400px]"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            <div className="flex items-center gap-2 w-full md:w-auto">
                <Popover>
                    <PopoverTrigger asChild>
                        <Button variant="outline" size="sm" className="h-9 gap-2 border-dashed">
                            <Filter className="w-3.5 h-3.5" />
                            {selectedModel ? models?.find(m => m.id === selectedModel)?.name : "Filter by Model"}
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent className="p-0 w-[200px]" align="end">
                        <Command>
                            <CommandInput placeholder="Select model..." />
                            <CommandList>
                                <CommandEmpty>No model found.</CommandEmpty>
                                <CommandGroup>
                                    <CommandItem
                                        value="all"
                                        onSelect={() => setSelectedModel(undefined)}
                                    >
                                        <Check className={cn("mr-2 h-4 w-4", !selectedModel ? "opacity-100" : "opacity-0")} />
                                        All Models
                                    </CommandItem>
                                    {models?.map((model) => (
                                        <CommandItem
                                            key={model.id}
                                            value={model.id}
                                            onSelect={(currentValue) => {
                                                setSelectedModel(currentValue === selectedModel ? undefined : currentValue)
                                            }}
                                        >
                                            <Check className={cn("mr-2 h-4 w-4", selectedModel === model.id ? "opacity-100" : "opacity-0")} />
                                            {model.name}
                                        </CommandItem>
                                    ))}
                                </CommandGroup>
                            </CommandList>
                        </Command>
                    </PopoverContent>
                </Popover>

                <Popover>
                    <PopoverTrigger asChild>
                        <Button variant="outline" size="sm" className={cn("h-9 gap-2 justify-start text-left font-normal", !date && "text-muted-foreground")}>
                            <CalendarIcon className="mr-2 h-4 w-4" />
                            {date ? format(date, "PPP") : <span>Pick a date</span>}
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="end">
                        <Calendar
                            mode="single"
                            selected={date}
                            onSelect={setDate}
                            initialFocus
                        />
                    </PopoverContent>
                </Popover>
            </div>
        </div>
    )
}
