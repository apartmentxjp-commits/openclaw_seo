"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle2, XCircle, Clock, Calendar, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

interface Post {
    id: string
    content: string
    status: string
    scheduledAt: string | null
    createdAt: string
    threadParts: string | null
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    PUBLISHED: { label: "投稿済み", color: "bg-green-500/10 text-green-400 border-green-500/30", icon: <CheckCircle2 className="h-3 w-3" /> },
    POSTED: { label: "投稿済み", color: "bg-green-500/10 text-green-400 border-green-500/30", icon: <CheckCircle2 className="h-3 w-3" /> },
    SCHEDULED: { label: "予約中", color: "bg-blue-500/10 text-blue-400 border-blue-500/30", icon: <Clock className="h-3 w-3" /> },
    FAILED: { label: "失敗", color: "bg-red-500/10 text-red-400 border-red-500/30", icon: <XCircle className="h-3 w-3" /> },
    DRAFT: { label: "下書き", color: "bg-gray-500/10 text-gray-400 border-gray-500/30", icon: <Calendar className="h-3 w-3" /> },
}

function formatDate(dateStr: string | null) {
    if (!dateStr) return "—"
    const d = new Date(dateStr)
    return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export default function HistoryPage() {
    const [posts, setPosts] = useState<Post[]>([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState("ALL")

    const fetchPosts = async () => {
        setLoading(true)
        try {
            const res = await fetch("/api/posts")
            const data = await res.json()
            if (data.success) {
                const sorted = [...data.posts].sort((a: Post, b: Post) =>
                    new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
                )
                setPosts(sorted)
            }
        } catch { toast.error("投稿の取得に失敗しました") }
        finally { setLoading(false) }
    }

    useEffect(() => { fetchPosts() }, [])

    const filtered = filter === "ALL" ? posts : posts.filter(p => p.status === filter)
    const counts = {
        ALL: posts.length,
        PUBLISHED: posts.filter(p => p.status === 'PUBLISHED' || p.status === 'POSTED').length,
        SCHEDULED: posts.filter(p => p.status === 'SCHEDULED').length,
        FAILED: posts.filter(p => p.status === 'FAILED').length,
        DRAFT: posts.filter(p => p.status === 'DRAFT').length,
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-700">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight">投稿履歴</h1>
                    <p className="text-muted-foreground mt-1">全ての投稿ステータスを確認できます</p>
                </div>
                <Button variant="outline" size="sm" onClick={fetchPosts} disabled={loading}>
                    <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    更新
                </Button>
            </div>

            {/* フィルタタブ */}
            <div className="flex gap-2 flex-wrap">
                {[
                    { key: "ALL", label: "すべて" },
                    { key: "PUBLISHED", label: "✅ 投稿済み" },
                    { key: "SCHEDULED", label: "⏳ 予約中" },
                    { key: "FAILED", label: "❌ 失敗" },
                    { key: "DRAFT", label: "📝 下書き" },
                ].map(tab => (
                    <button
                        key={tab.key}
                        onClick={() => setFilter(tab.key)}
                        className={`text-sm px-3 py-1.5 rounded-full border transition-colors font-medium ${filter === tab.key
                                ? "bg-primary text-primary-foreground border-primary"
                                : "border-border text-muted-foreground hover:text-foreground"
                            }`}
                    >
                        {tab.label} <span className="ml-1 opacity-60">{counts[tab.key as keyof typeof counts]}</span>
                    </button>
                ))}
            </div>

            {/* 投稿リスト */}
            {loading ? (
                <div className="text-center py-20 text-muted-foreground">読み込み中...</div>
            ) : filtered.length === 0 ? (
                <div className="text-center py-20 text-muted-foreground">該当する投稿がありません</div>
            ) : (
                <div className="space-y-3">
                    {filtered.map(post => {
                        const sc = STATUS_CONFIG[post.status] || STATUS_CONFIG["DRAFT"]
                        const parts = post.threadParts ? JSON.parse(post.threadParts) : [post.content]
                        return (
                            <Card key={post.id} className="glass border-border/50">
                                <CardContent className="p-4">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex-1 min-w-0">
                                            {parts.map((part: string, i: number) => (
                                                <div key={i} className={i > 0 ? "mt-2 pt-2 border-t border-border/40" : ""}>
                                                    {i > 0 && <span className="text-xs text-muted-foreground mr-1">↳</span>}
                                                    <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{part}</p>
                                                </div>
                                            ))}
                                        </div>
                                        <div className="flex flex-col items-end gap-2 shrink-0">
                                            <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium ${sc.color}`}>
                                                {sc.icon} {sc.label}
                                            </span>
                                            <span className="text-xs text-muted-foreground">
                                                {formatDate(post.scheduledAt || post.createdAt)}
                                            </span>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
