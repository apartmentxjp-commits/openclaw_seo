"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Plus, Trash2, Clock, Loader2, CalendarRange, Sparkles, ChevronRight } from "lucide-react"
import { toast } from "sonner"

interface ScheduleItem {
    id?: string;
    time: string;
    active: boolean;
}

export default function SchedulesPage() {
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [schedules, setSchedules] = useState<ScheduleItem[]>([])

    useEffect(() => {
        const fetchSchedules = async () => {
            try {
                const res = await fetch("/api/schedules")
                const data = await res.json()
                if (data.success) {
                    setSchedules(data.schedules.length > 0 ? data.schedules : [{ time: "08:00", active: true }])
                }
            } catch (error) {
                console.error("Failed to fetch schedules:", error)
            } finally {
                setLoading(false)
            }
        }
        fetchSchedules()
    }, [])

    const addSchedule = () => {
        setSchedules([...schedules, { time: "12:00", active: true }])
    }

    const removeSchedule = (index: number) => {
        if (schedules.length <= 1) {
            toast.error("少なくとも1つの投稿時間が必要です")
            return
        }
        setSchedules(schedules.filter((_, i) => i !== index))
    }

    const updateTime = (index: number, newTime: string) => {
        const newSchedules = [...schedules]
        newSchedules[index].time = newTime
        setSchedules(newSchedules)
    }

    const handleSave = async () => {
        setSaving(true)
        try {
            const res = await fetch("/api/schedules", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ schedules })
            })
            const data = await res.json()
            if (data.success) {
                toast.success("スケジュールを保存しました")
            } else {
                toast.error("保存失敗: " + data.error)
            }
        } catch (error) {
            toast.error("通信エラーが発生しました")
        } finally {
            setSaving(false)
        }
    }

    if (loading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Loader2 className="h-10 w-10 animate-spin text-primary/40" />
            </div>
        )
    }

    return (
        <div className="space-y-10 max-w-4xl mx-auto pb-20 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex flex-col space-y-2">
                <h1 className="text-4xl font-extrabold tracking-tight">
                    <span className="premium-gradient-text">投稿リズム</span> を刻む
                </h1>
                <p className="text-muted-foreground text-lg">
                    あなたの発信スタイルに合わせて、最適な時間をスケジューリング。
                </p>
            </div>

            <Card className="glass-card border-none shadow-2xl overflow-hidden">
                <CardHeader className="p-8 border-b border-border/10 bg-white/30 dark:bg-white/5">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-primary/10 rounded-2xl">
                            <CalendarRange className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                            <CardTitle className="text-xl font-bold">1日の投稿タイムライン</CardTitle>
                            <p className="text-xs text-muted-foreground mt-1">
                                スロットを追加して、自動投稿のタイミングをカスタマイズします。
                            </p>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-8 space-y-8">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {schedules.map((schedule, index) => (
                            <div
                                key={index}
                                className="group flex items-center gap-4 p-5 glass rounded-2xl border border-border/50 hover:border-primary/50 transition-all duration-300 hover:shadow-lg hover:bg-white/80 dark:hover:bg-white/10"
                            >
                                <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 text-primary font-black text-lg">
                                    {index + 1}
                                </div>
                                <div className="flex-1 space-y-2">
                                    <div className="flex items-center gap-2">
                                        <Clock className="h-3 w-3 text-muted-foreground" />
                                        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Posting Slot</span>
                                    </div>
                                    <Input
                                        type="time"
                                        value={schedule.time}
                                        onChange={(e) => updateTime(index, e.target.value)}
                                        className="h-12 text-lg font-bold bg-transparent border-none focus-visible:ring-0 p-0 shadow-none cursor-pointer"
                                    />
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => removeSchedule(index)}
                                    className="h-10 w-10 text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-colors opacity-0 group-hover:opacity-100"
                                >
                                    <Trash2 className="h-5 w-5" />
                                </Button>
                            </div>
                        ))}

                        <button
                            onClick={addSchedule}
                            className="flex flex-col items-center justify-center gap-2 p-5 border-2 border-dashed border-primary/20 rounded-2xl hover:bg-primary/5 transition-all group"
                        >
                            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                                <Plus className="h-5 w-5 text-primary" />
                            </div>
                            <span className="text-sm font-bold text-primary/60">新しいスロットを追加</span>
                        </button>
                    </div>

                    <div className="p-6 rounded-2xl glass-card bg-primary/5 border-primary/10">
                        <div className="flex items-start gap-4">
                            <div className="p-2 bg-primary/20 rounded-lg">
                                <Sparkles className="h-4 w-4 text-primary" />
                            </div>
                            <div className="space-y-1">
                                <h4 className="text-sm font-bold text-primary">AIとのシームレスな連携</h4>
                                <p className="text-xs text-muted-foreground leading-relaxed italic">
                                    「ここで設定した時間は、投稿生成画面での一括予約時に自動的に適用されます。ターゲットが最もアクティブな時間を選択することで、エンゲージメントを最大化できます。」
                                </p>
                            </div>
                        </div>
                    </div>
                </CardContent>
                <CardFooter className="p-8 border-t border-border/10 bg-black/5 dark:bg-white/5 flex items-center justify-between">
                    <div className="text-sm text-muted-foreground flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                        現在は 1日 <b>{schedules.length} 回</b> の投稿を予定しています。
                    </div>
                    <Button onClick={handleSave} disabled={saving} className="premium-button px-10 py-6 rounded-2xl group">
                        {saving ? (
                            <Loader2 className="h-5 w-5 animate-spin" />
                        ) : (
                            <>
                                変更内容を同期する
                                <ChevronRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                            </>
                        )}
                    </Button>
                </CardFooter>
            </Card>
        </div>
    )
}
