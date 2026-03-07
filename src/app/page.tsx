"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import {
  BarChart3,
  Calendar as CalendarIcon,
  CheckCircle2,
  Clock,
  MessageSquare,
  TrendingUp,
  XCircle,
  ArrowRight,
  Zap
} from "lucide-react"
import { Button } from "@/components/ui/button"

interface Post {
  id: string
  content: string
  status: string
  scheduledAt: string | null
  createdAt: string
  threadParts: string | null
}

// フェーズ判定（投稿総数ベース）
function getPhase(total: number) {
  if (total < 30) return { phase: 1, label: "Phase 1 — ゼロから始まる", color: "text-blue-400", progress: Math.round((total / 30) * 100) }
  if (total < 60) return { phase: 2, label: "Phase 2 — 光が見えてきた", color: "text-indigo-400", progress: Math.round(((total - 30) / 30) * 100) }
  return { phase: 3, label: "Phase 3 — 形になってきた", color: "text-purple-400", progress: Math.min(Math.round(((total - 60) / 30) * 100), 100) }
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return "—"
  const d = new Date(dateStr)
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export default function Dashboard() {
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [hasAccount, setHasAccount] = useState(true)

  useEffect(() => {
    fetch("/api/posts").then(r => r.json()).then(data => {
      if (data.success) setPosts(data.posts)
    }).catch(() => { })

    fetch("/api/accounts").then(r => r.json()).then(data => {
      if (data.success) setHasAccount(data.accounts.length > 0)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const total = posts.length
  const scheduled = posts.filter(p => p.status === 'SCHEDULED').length
  const published = posts.filter(p => p.status === 'PUBLISHED' || p.status === 'POSTED').length
  const failed = posts.filter(p => p.status === 'FAILED').length
  const phaseInfo = getPhase(published)

  const recent = [...posts]
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, 5)

  const failedPosts = posts.filter(p => p.status === 'FAILED').slice(0, 3)

  return (
    <div className="space-y-6 animate-in fade-in duration-700 pb-20 lg:pb-0">
      <div className="flex flex-col space-y-1">
        <h1 className="text-3xl font-extrabold tracking-tight">
          ダッシュボード
        </h1>
        <p className="text-muted-foreground">
          今日の投稿状況とアカウントの成長フェーズ
        </p>
      </div>

      {!hasAccount && !loading && (
        <Card className="border-red-500/50 bg-red-500/10 animate-pulse transition-all">
          <CardContent className="p-4 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <XCircle className="h-6 w-6 text-red-500" />
              <div>
                <p className="text-sm font-bold text-red-100">SNSアカウントが連携されていません</p>
                <p className="text-xs text-red-200/70">投稿を予約しても、実行するためには「設定 &gt; アカウント連携」からXとの連携が必要です。</p>
              </div>
            </div>
            <Button asChild size="sm" variant="destructive" className="font-bold">
              <Link href="/integrations">連携しにいく</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {/* フェーズ表示バナー */}
      <Card className="glass-card border-primary/20 bg-gradient-to-r from-primary/5 to-transparent">
        <CardContent className="p-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10">
                <Zap className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground font-medium">現在のフェーズ</p>
                <p className={`font-bold text-sm ${phaseInfo.color}`}>{phaseInfo.label}</p>
              </div>
            </div>
            <div className="flex-1 max-w-[200px]">
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>投稿済み {published}件</span>
                <span>{phaseInfo.progress}%</span>
              </div>
              <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-1000"
                  style={{ width: `${phaseInfo.progress}%` }}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* サマリーカード */}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        <StatsCard title="総投稿数" value={total} icon={MessageSquare} color="blue" />
        <StatsCard title="予約中" value={scheduled} icon={CalendarIcon} color="indigo" />
        <StatsCard title="投稿済み" value={published} icon={CheckCircle2} color="emerald" />
        <StatsCard title="失敗" value={failed} icon={XCircle} color={failed > 0 ? "red" : "gray"} />
      </div>

      <div className="grid gap-6 lg:grid-cols-7">
        {/* 直近の投稿リスト */}
        <Card className="col-span-4 glass-card">
          <CardHeader className="flex flex-row items-center justify-between border-b bg-white/50 dark:bg-white/5 pb-3">
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Clock className="h-4 w-4 text-primary" /> 最近の投稿
            </CardTitle>
            <Link href="/history" className="text-xs text-muted-foreground hover:text-primary flex items-center gap-1">
              すべて見る <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-8 text-center text-sm text-muted-foreground">読み込み中...</div>
            ) : recent.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">投稿がありません</div>
            ) : (
              <div className="divide-y divide-border/40">
                {recent.map(post => {
                  const parts = post.threadParts ? JSON.parse(post.threadParts) : [post.content]
                  const preview = parts[0]?.slice(0, 60) + (parts[0]?.length > 60 ? "…" : "")
                  const statusColor = {
                    PUBLISHED: "text-green-400", POSTED: "text-green-400",
                    SCHEDULED: "text-blue-400", FAILED: "text-red-400", DRAFT: "text-gray-400"
                  }[post.status] || "text-gray-400"
                  return (
                    <div key={post.id} className="px-4 py-3 flex items-start gap-3 hover:bg-white/30 dark:hover:bg-white/5 transition-colors">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm truncate">{preview}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{formatDate(post.scheduledAt || post.createdAt)}</p>
                      </div>
                      <span className={`text-xs font-medium shrink-0 ${statusColor}`}>
                        {post.status === 'PUBLISHED' || post.status === 'POSTED' ? '✅' :
                          post.status === 'SCHEDULED' ? '⏳' :
                            post.status === 'FAILED' ? '❌' : '📝'}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 右カラム */}
        <div className="col-span-3 space-y-4">
          {/* 失敗投稿アラート */}
          {failedPosts.length > 0 && (
            <Card className="glass-card border-red-500/20">
              <CardHeader className="pb-2 border-b border-red-500/10">
                <CardTitle className="text-sm font-bold text-red-400 flex items-center gap-2">
                  <XCircle className="h-4 w-4" /> 失敗した投稿 ({failed}件)
                </CardTitle>
              </CardHeader>
              <CardContent className="p-3 space-y-2">
                {failedPosts.map(post => {
                  const parts = post.threadParts ? JSON.parse(post.threadParts) : [post.content]
                  return (
                    <div key={post.id} className="text-xs p-2 rounded-lg bg-red-500/5 border border-red-500/10">
                      <p className="truncate text-red-300/80">{parts[0]?.slice(0, 50)}…</p>
                      <p className="text-red-400/50 mt-0.5">{formatDate(post.scheduledAt)}</p>
                    </div>
                  )
                })}
              </CardContent>
            </Card>
          )}

          {/* クイックアクション */}
          <Card className="glass-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-bold">クイックアクション</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {[
                { href: "/posts", label: "📝 投稿を生成する", desc: "AIで一括生成" },
                { href: "/history", label: "📋 投稿履歴を確認", desc: "ステータス確認" },
                { href: "/schedules", label: "⏰ 投稿時間を設定", desc: "スケジュール管理" },
              ].map(item => (
                <Link key={item.href} href={item.href}
                  className="flex items-center justify-between p-3 rounded-xl hover:bg-white/50 dark:hover:bg-white/5 border border-transparent hover:border-border transition-all group"
                >
                  <div>
                    <p className="text-sm font-medium">{item.label}</p>
                    <p className="text-xs text-muted-foreground">{item.desc}</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                </Link>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function StatsCard({ title, value, icon: Icon, color }: any) {
  const colors: any = {
    blue: "text-blue-600 bg-blue-50 dark:bg-blue-900/20",
    indigo: "text-indigo-600 bg-indigo-50 dark:bg-indigo-900/20",
    emerald: "text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20",
    purple: "text-purple-600 bg-purple-50 dark:bg-purple-900/20",
    red: "text-red-500 bg-red-50 dark:bg-red-900/20",
    gray: "text-gray-400 bg-gray-50 dark:bg-gray-900/20",
  }
  return (
    <Card className="glass-card">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-xs font-semibold text-muted-foreground">{title}</CardTitle>
        <div className={`p-1.5 rounded-lg ${colors[color]}`}>
          <Icon className="h-3.5 w-3.5" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  )
}
