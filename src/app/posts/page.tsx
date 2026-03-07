"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Loader2, Plus, Sparkles, Send, Copy, Zap, MessageSquare, TrendingUp, PenTool, Newspaper, Shuffle } from "lucide-react"

interface Post {
    content: string;
    dayOffset: number;
    threadParts?: string[] | null;
    asset?: string | null;
}

const STRATEGIES = [
    {
        id: "mix",
        name: "おまかせミックス",
        icon: Shuffle,
        description: "複数の戦略を組み合わせて最適なバランスで運用。"
    },
    {
        id: "educational",
        name: "有益・教育型",
        icon: Zap,
        description: "AIノウハウ・Tipsを解説し、信頼と専門性を獲得。"
    },
    {
        id: "story",
        name: "共感・ストーリー型",
        icon: MessageSquare,
        description: "自身の経験・失敗談でファンを作る感情型投稿。"
    },
    {
        id: "argument",
        name: "議論・主張型",
        icon: TrendingUp,
        description: "独自の視点・逆説で議論とコメントを誘発。"
    },
    {
        id: "news_curation",
        name: "世界AI最前線",
        icon: Newspaper,
        description: "日本未上陸の最新AI動向を独自視点で解説。"
    },
]

export default function PostsPage() {
    const [strategy, setStrategy] = useState("educational")
    const [days, setDays] = useState("3")
    const [topic, setTopic] = useState("")
    const [referencePost, setReferencePost] = useState("")
    const [profile, setProfile] = useState<any>(null)
    const [isLoading, setIsLoading] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [generatedPosts, setGeneratedPosts] = useState<Post[]>([])
    const [autoLike, setAutoLike] = useState(false)
    const [autoRepost, setAutoRepost] = useState(false)
    const [trends, setTrends] = useState<{ keyword: string; traffic: string }[]>([])
    const [isTrendLoading, setIsTrendLoading] = useState(false)
    const [editingIdx, setEditingIdx] = useState<number | null>(null)

    // プロフィール情報の取得（useEffectで一度だけ実行）
    useEffect(() => {
        fetch("/api/profile").then(res => res.json()).then(data => {
            if (data.success) setProfile(data.profile)
        })
    }, [])

    // AI一括生成
    const handleGenerate = async () => {
        if (!topic && !referencePost) {
            toast.error("トピックまたはお手本投稿を入力してください")
            return
        }
        setIsLoading(true)
        try {
            const res = await fetch("/api/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    strategy: strategy,
                    strategyName: STRATEGIES.find(s => s.id === strategy)?.name,
                    dayCount: parseInt(days),
                    topic: topic,
                    referencePost: referencePost,
                    profile: profile
                })
            })
            const data = await res.json()
            if (data.success && data.posts) {
                setGeneratedPosts(data.posts)
                toast.success(`${data.posts.length}件の投稿案を作成しました`)
            } else {
                toast.error("生成に失敗しました: " + data.error)
            }
        } catch (error) {
            toast.error("サーバーエラーが発生しました")
        } finally {
            setIsLoading(false)
        }
    }

    // 生成された投稿をDBへ保存
    const handleSaveToCalendar = async (post: Post) => {
        setIsSaving(true)
        try {
            const res = await fetch("/api/posts", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(post)
            })
            const data = await res.json()
            if (data.success) {
                toast.success("カレンダーに保存しました")
                setGeneratedPosts(prev => prev.filter(p => p !== post))
            }
        } catch (error) {
            toast.error("保存エラーが発生しました")
        } finally {
            setIsSaving(false)
        }
    }

    // 一括保存
    const handleBatchSave = async () => {
        setIsSaving(true)
        try {
            const schedRes = await fetch("/api/schedules")
            const schedData = await schedRes.json()
            let activeSchedules = schedData.schedules?.filter((s: any) => s.active) || []

            // スケジュールが空の場合はデフォルト値を適用
            if (activeSchedules.length === 0) {
                activeSchedules = [{ time: "08:00" }]
                toast.info("投稿時間を設定していないため、デフォルトの 08:00 に予約しました")
            }

            const postsToSave = generatedPosts.map((post, index) => {
                const schedule = activeSchedules[index % activeSchedules.length];
                const date = new Date();
                date.setDate(date.getDate() + post.dayOffset);
                const [hours, minutes] = schedule.time.split(':');
                date.setHours(parseInt(hours), parseInt(minutes), 0, 0);

                return {
                    content: post.content,
                    scheduledAt: date.toISOString(),
                    timeString: schedule.time,
                    autoLike: autoLike,
                    autoRepost: autoRepost,
                    asset: post.asset || null,
                    threadParts: post.threadParts || null,
                    status: 'SCHEDULED'
                };
            });

            const res = await fetch("/api/posts", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ posts: postsToSave, isBatch: true })
            })

            const data = await res.json()
            if (data.success) {
                toast.success(`${data.count}件予約しました`)
                setGeneratedPosts([])
            }
        } catch (error) {
            toast.error("一括保存エラー")
        } finally {
            setIsSaving(false)
        }
    }

    return (
        <div className="space-y-10 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex flex-col space-y-2">
                <h1 className="text-4xl font-extrabold tracking-tight">
                    投稿を <span className="premium-gradient-text">デザイン</span> する
                </h1>
                <p className="text-muted-foreground text-lg">
                    AIがあなたの代わりに最高の一言をプロデュースします。
                </p>
            </div>

            <Tabs defaultValue="auto" className="w-full">
                <TabsList className="glass p-1 rounded-2xl mb-8">
                    <TabsTrigger value="auto" className="rounded-xl px-8 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">AI自動生成</TabsTrigger>
                    <TabsTrigger value="manual" className="rounded-xl px-8 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">手動作成</TabsTrigger>
                </TabsList>

                <TabsContent value="auto" className="space-y-6">
                    <Card className="glass-card p-2">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-xl">
                                <Sparkles className="h-5 w-5 text-primary animate-pulse" />
                                生成のコンテキストを設定
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-3">
                                    <Label className="text-sm font-bold">投稿戦略</Label>
                                    <div className="grid grid-cols-2 gap-2">
                                        {STRATEGIES.map((s) => (
                                            <button
                                                key={s.id}
                                                onClick={() => setStrategy(s.id)}
                                                className={`p-3 text-left rounded-xl border transition-all ${strategy === s.id
                                                    ? 'border-primary bg-primary/5 shadow-sm'
                                                    : 'border-border bg-white/50 dark:bg-white/5 hover:border-primary/50'
                                                    }`}
                                            >
                                                <s.icon className={`h-4 w-4 mb-2 ${strategy === s.id ? 'text-primary' : 'text-muted-foreground'}`} />
                                                <div className="text-xs font-bold">{s.name}</div>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <div className="space-y-3">
                                    <Label className="text-sm font-bold">期間設定</Label>
                                    <Select value={days} onValueChange={setDays}>
                                        <SelectTrigger className="glass py-6"><SelectValue /></SelectTrigger>
                                        <SelectContent className="glass border-none">
                                            <SelectItem value="3">3日間（ショートプラン）</SelectItem>
                                            <SelectItem value="7">7日間（ウィークリープラン）</SelectItem>
                                            <SelectItem value="30">30日間（マンスリーフルプラン）</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <div className="p-4 rounded-xl bg-orange-50/50 dark:bg-orange-500/5 border border-orange-100 dark:border-orange-500/10 mt-2">
                                        <p className="text-[10px] text-orange-600 dark:text-orange-400 leading-relaxed font-medium">
                                            💡 現在の設定：1日 {profile?.postsPerDay || 1} 回投稿予定。一括生成で合計{parseInt(days) * (profile?.postsPerDay || 1)}件作成。
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <hr className="border-border/50" />

                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <Label className="text-sm font-bold flex items-center gap-2">
                                        <Copy className="h-4 w-4 text-muted-foreground" />
                                        お手本にする投稿文
                                    </Label>
                                    <Textarea
                                        placeholder="真似したい文体やリズムをここに貼り付けます..."
                                        value={referencePost}
                                        onChange={(e) => setReferencePost(e.target.value)}
                                        className="min-h-[120px] glass resize-none focus-visible:ring-primary"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <Label className="text-sm font-bold flex items-center gap-2">
                                            <PenTool className="h-4 w-4 text-muted-foreground" />
                                            具体的に盛り込みたいトピック
                                        </Label>
                                        <button
                                            type="button"
                                            onClick={async () => {
                                                setIsTrendLoading(true)
                                                try {
                                                    const res = await fetch('/api/trends')
                                                    const data = await res.json()
                                                    if (data.success) setTrends(data.trends.slice(0, 10))
                                                } catch { toast.error('トレンド取得に失敗しました') }
                                                finally { setIsTrendLoading(false) }
                                            }}
                                            className="text-xs flex items-center gap-1 text-orange-400 hover:text-orange-300 transition-colors font-bold"
                                        >
                                            {isTrendLoading ? '取得中...' : '🔥 今日のトレンド'}
                                        </button>
                                    </div>
                                    <Input
                                        placeholder="例: 副業を始めるためのマインドセット"
                                        value={topic}
                                        onChange={(e) => setTopic(e.target.value)}
                                        className="glass py-6 focus-visible:ring-primary"
                                    />
                                    {trends.length > 0 && (
                                        <div className="flex flex-wrap gap-2 pt-1">
                                            {trends.map((t, i) => (
                                                <button
                                                    key={i}
                                                    type="button"
                                                    onClick={() => setTopic(t.keyword)}
                                                    className="text-xs px-2 py-1 rounded-full bg-orange-500/10 border border-orange-500/30 text-orange-300 hover:bg-orange-500/20 transition-colors"
                                                >
                                                    {t.keyword} <span className="opacity-60">{t.traffic}</span>
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                <div className="flex items-center gap-6 pt-2">
                                    <label className="flex items-center gap-2 cursor-pointer group">
                                        <input
                                            type="checkbox"
                                            checked={autoLike}
                                            onChange={(e) => setAutoLike(e.target.checked)}
                                            className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                                        />
                                        <span className="text-xs font-bold group-hover:text-primary transition-colors">自動いいね</span>
                                    </label>
                                    <label className="flex items-center gap-2 cursor-pointer group">
                                        <input
                                            type="checkbox"
                                            checked={autoRepost}
                                            onChange={(e) => setAutoRepost(e.target.checked)}
                                            className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                                        />
                                        <span className="text-xs font-bold group-hover:text-primary transition-colors">自動リポスト</span>
                                    </label>
                                </div>
                            </div>
                        </CardContent>
                        <CardFooter>
                            <Button onClick={handleGenerate} disabled={isLoading} className="premium-button w-full py-7 text-lg group">
                                {isLoading ? (
                                    <Loader2 className="h-5 w-5 animate-spin" />
                                ) : (
                                    <>
                                        AIで魔法をかける
                                        <Sparkles className="ml-2 h-5 w-5 group-hover:rotate-12 transition-transform" />
                                    </>
                                )}
                            </Button>
                        </CardFooter>
                    </Card>
                </TabsContent>

                <TabsContent value="manual">
                    <Card className="glass-card">
                        <CardContent className="pt-6">
                            <Textarea placeholder="今、伝えたいことを自由に..." className="min-h-[200px] glass" />
                        </CardContent>
                        <CardFooter className="justify-end gap-2">
                            <Button variant="ghost">下書き</Button>
                            <Button className="premium-button px-8">保存</Button>
                        </CardFooter>
                    </Card>
                </TabsContent>
            </Tabs>

            {generatedPosts.length > 0 && (
                <div className="space-y-6 pt-10">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                            <h3 className="text-2xl font-bold">AIからの <span className="premium-gradient-text">提案</span></h3>
                            <p className="text-sm text-muted-foreground">内容を確認してカレンダーへ予約してください。</p>
                        </div>
                        <Button
                            className="bg-emerald-600 hover:bg-emerald-700 shadow-lg shadow-emerald-500/20 text-white font-bold py-6 px-8 rounded-2xl"
                            onClick={handleBatchSave}
                            disabled={isSaving}
                        >
                            {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="mr-2 h-4 w-4" />}
                            全て一括でカレンダー予約
                        </Button>
                    </div>

                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-2">
                        {generatedPosts.map((post, idx) => (
                            <Card key={idx} className="glass border-primary/10 overflow-hidden group hover:border-primary/30 transition-all">
                                <CardHeader className="py-3 px-4 bg-muted/30 flex flex-row items-center justify-between">
                                    <span className="text-[10px] font-black uppercase tracking-tighter opacity-50">Day +{post.dayOffset}</span>
                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <Sparkles className="h-3 w-3 text-primary" />
                                        <span className="text-[9px] font-bold">AI Analysis Optimized</span>
                                    </div>
                                </CardHeader>
                                <CardContent className="p-6">
                                    {/* スレッド投稿の場合はスレッド形式で表示 */}
                                    {post.threadParts && Array.isArray(post.threadParts) && post.threadParts.length > 1 ? (
                                        <div className="space-y-2 mb-4">
                                            <div className="flex items-center gap-1 mb-3">
                                                <span className="text-[10px] font-bold text-blue-500 bg-blue-500/10 px-2 py-0.5 rounded-full">🧵 スレッド連投 {post.threadParts.length}件</span>
                                            </div>
                                            {post.threadParts.map((part: string, ti: number) => (
                                                <div key={ti} className="flex gap-2">
                                                    <div className="flex flex-col items-center">
                                                        <div className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center text-[9px] font-bold text-primary flex-shrink-0">{ti + 1}</div>
                                                        {ti < post.threadParts!.length - 1 && <div className="w-0.5 flex-1 bg-primary/10 mt-1" />}
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        {editingIdx === idx ? (
                                                            <Textarea
                                                                value={part}
                                                                className="text-sm min-h-[80px] glass mb-3"
                                                                onChange={(e) => {
                                                                    const newPosts = [...generatedPosts];
                                                                    const newParts = [...(newPosts[idx].threadParts || [])];
                                                                    newParts[ti] = e.target.value;
                                                                    newPosts[idx].threadParts = newParts;
                                                                    setGeneratedPosts(newPosts);
                                                                }}
                                                            />
                                                        ) : (
                                                            <div className="text-sm leading-relaxed pb-3 whitespace-pre-wrap">{part}</div>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        editingIdx === idx ? (
                                            <Textarea
                                                value={post.content}
                                                className="text-sm min-h-[120px] glass mb-4"
                                                onChange={(e) => {
                                                    const newPosts = [...generatedPosts];
                                                    newPosts[idx].content = e.target.value;
                                                    setGeneratedPosts(newPosts);
                                                }}
                                            />
                                        ) : (
                                            <div className="whitespace-pre-wrap text-sm leading-relaxed mb-4">{post.content}</div>
                                        )
                                    )}

                                    {post.asset && (
                                        <div className="mt-4 p-4 rounded-xl bg-primary/5 border border-primary/20 relative group/asset">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-[10px] font-bold text-primary flex items-center gap-1">
                                                    <Zap className="h-3 w-3" /> 特典アセット（配布ノート）
                                                </span>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-6 px-2 text-[9px] hover:bg-primary/10"
                                                    onClick={() => {
                                                        navigator.clipboard.writeText(post.asset || "");
                                                        toast.success("特典内容をコピーしました");
                                                    }}
                                                >
                                                    コピー
                                                </Button>
                                            </div>
                                            <div className="text-[11px] text-muted-foreground line-clamp-3 italic">
                                                {post.asset}
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                                <CardFooter className="bg-white/30 dark:bg-white/5 py-4 border-t flex justify-end gap-2">
                                    {editingIdx === idx ? (
                                        <Button
                                            size="sm"
                                            className="bg-emerald-600 hover:bg-emerald-700 text-white"
                                            onClick={() => setEditingIdx(null)}
                                        >
                                            完了
                                        </Button>
                                    ) : (
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="text-xs group-hover:text-primary"
                                            onClick={() => setEditingIdx(idx)}
                                        >
                                            編集
                                        </Button>
                                    )}
                                    <Button
                                        size="sm"
                                        className="bg-primary/10 text-primary hover:bg-primary hover:text-white transition-all rounded-lg font-bold"
                                        onClick={() => handleSaveToCalendar(post)}
                                        disabled={isSaving || editingIdx === idx}
                                    >
                                        カレンダーに採用
                                    </Button>
                                </CardFooter>
                            </Card>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}


