"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import { Loader2, User, Target, Zap, Feather, Sparkles, ChevronRight, Save } from "lucide-react"

export default function ProfilePage() {
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [profile, setProfile] = useState({
        accountName: "",
        industry: "",
        targetAudience: "",
        tone: "",
        background: "",
        postsPerDay: 1,
        discordWebhookUrl: "",
        telegramBotToken: "",
        telegramChatId: ""
    })
    const [xAccount, setXAccount] = useState<any>(null)
    const [checkingX, setCheckingX] = useState(true)

    const fetchProfile = async () => {
        try {
            const res = await fetch("/api/profile")
            const data = await res.json()
            if (data.success && data.profile) {
                setProfile(data.profile)
            }

            // X連携状態の取得
            const xRes = await fetch("/api/auth/x/status")
            const xData = await xRes.json()
            if (xData.success) {
                setXAccount(xData.account)
            }
        } catch (error) {
            console.error("Failed to fetch profile:", error)
        } finally {
            setLoading(false)
            setCheckingX(false)
        }
    }

    const handleConnectX = () => {
        window.location.href = "/api/auth/x"
    }

    const handleDisconnectX = async () => {
        if (!confirm("Xアカウントの連携を解除しますか？")) return
        try {
            const res = await fetch("/api/auth/x", { method: "DELETE" })
            if (res.ok) {
                toast.success("連携を解除しました")
                setXAccount(null)
            }
        } catch (error) {
            toast.error("解除に失敗しました")
        }
    }

    useEffect(() => {
        fetchProfile()
    }, [])

    const handleSave = async () => {
        setSaving(true)
        try {
            const res = await fetch("/api/profile", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(profile)
            })
            const data = await res.json()
            if (data.success) {
                toast.success("プロフィールを保存しました")
                await fetchProfile() // 保存後に再取得して同期
            } else {
                toast.error("保存に失敗しました: " + data.error)
            }
        } catch (error) {
            toast.error("サーバーエラーが発生しました")
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
        <div className="space-y-10 max-w-5xl mx-auto pb-20 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex flex-col space-y-2">
                <h1 className="text-4xl font-extrabold tracking-tight">
                    AIの <span className="premium-gradient-text">DNA</span> を定義する
                </h1>
                <p className="text-muted-foreground text-lg">
                    あなたの「自分らしさ」をAIに共有。
                    より一貫性と説得力のある発信を実現します。
                </p>
            </div>

            <div className="grid gap-8 md:grid-cols-2">
                <Card className="glass-card border-none shadow-2xl relative overflow-hidden">
                    <CardHeader className="p-8 border-b border-border/10">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-primary/10 rounded-2xl">
                                <User className="h-6 w-6 text-primary" />
                            </div>
                            <div>
                                <CardTitle className="text-xl font-bold">コア・アイデンティティ</CardTitle>
                                <p className="text-xs text-muted-foreground mt-1">
                                    アカウントの基本となる情報です。
                                </p>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent className="p-8 space-y-6">
                        <div className="space-y-3">
                            <Label htmlFor="accountName" className="text-xs font-black uppercase tracking-widest text-muted-foreground">アカウント名 / 著者名</Label>
                            <Input
                                id="accountName"
                                placeholder="例: たろう @Webエンジニア"
                                value={profile.accountName || ""}
                                onChange={(e) => setProfile({ ...profile, accountName: e.target.value })}
                                className="h-12 bg-white/50 dark:bg-black/20 border-border/50 rounded-xl focus:ring-primary/20 transition-all font-medium"
                            />
                        </div>

                        <div className="space-y-3">
                            <Label htmlFor="industry" className="text-xs font-black uppercase tracking-widest text-muted-foreground">業界 / ジャンル</Label>
                            <Input
                                id="industry"
                                placeholder="例: Web開発, AI, マーケティング"
                                value={profile.industry || ""}
                                onChange={(e) => setProfile({ ...profile, industry: e.target.value })}
                                className="h-12 bg-white/50 dark:bg-black/20 border-border/50 rounded-xl focus:ring-primary/20 transition-all font-medium"
                            />
                        </div>

                        <div className="space-y-3">
                            <Label htmlFor="targetAudience" className="text-xs font-black uppercase tracking-widest text-muted-foreground">ターゲット層</Label>
                            <Input
                                id="targetAudience"
                                placeholder="例: 初心者エンジニア、フリーランス志望者"
                                value={profile.targetAudience || ""}
                                onChange={(e) => setProfile({ ...profile, targetAudience: e.target.value })}
                                className="h-12 bg-white/50 dark:bg-black/20 border-border/50 rounded-xl focus:ring-primary/20 transition-all font-medium"
                            />
                        </div>

                        <div className="space-y-3">
                            <Label htmlFor="postsPerDay" className="text-xs font-black uppercase tracking-widest text-muted-foreground">1日あたりの投稿頻度</Label>
                            <Select
                                value={String(profile.postsPerDay || 1)}
                                onValueChange={(v) => setProfile({ ...profile, postsPerDay: parseInt(v) })}
                            >
                                <SelectTrigger className="h-12 bg-white/50 dark:bg-black/20 border-border/50 rounded-xl shadow-inner">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="glass shadow-2xl border-none">
                                    {[1, 2, 3, 4, 5].map(n => (
                                        <SelectItem key={n} value={String(n)} className="rounded-lg">{n} 回 / 日</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <p className="text-[10px] text-muted-foreground italic px-1">※AI一括生成時に、この回数分を1日に割り当てます。</p>
                        </div>
                    </CardContent>
                </Card>

                <div className="space-y-8">
                    <Card className="glass-card border-none shadow-2xl relative overflow-hidden">
                        <CardHeader className="p-8 border-b border-border/10">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-primary/10 rounded-2xl">
                                    <Zap className="h-6 w-6 text-primary" />
                                </div>
                                <div>
                                    <CardTitle className="text-xl font-bold">コンテキスト・ブースト</CardTitle>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        文章に魂を込めるための詳細情報です。
                                    </p>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="p-8 space-y-6">
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <Label htmlFor="tone" className="text-xs font-black uppercase tracking-widest text-muted-foreground">語り口（トーン＆マナー）</Label>
                                    <Sparkles className="h-3 w-3 text-primary/40" />
                                </div>
                                <Input
                                    id="tone"
                                    placeholder="例: 専門的だがわかりやすく、少しフレンドリー"
                                    value={profile.tone || ""}
                                    onChange={(e) => setProfile({ ...profile, tone: e.target.value })}
                                    className="h-12 bg-white/50 dark:bg-black/20 border-border/50 rounded-xl focus:ring-primary/20 transition-all font-medium"
                                />
                            </div>

                            <div className="space-y-3">
                                <Label htmlFor="background" className="text-xs font-black uppercase tracking-widest text-muted-foreground">経歴・実績・バックグラウンド</Label>
                                <Textarea
                                    id="background"
                                    placeholder="例: 上場企業で10年エンジニアを経験後、独立。これまでに20以上のプロダクトを開発..."
                                    className="min-h-[148px] bg-white/50 dark:bg-black/20 border-border/50 rounded-xl focus:ring-primary/20 transition-all font-medium leading-relaxed"
                                    value={profile.background || ""}
                                    onChange={(e) => setProfile({ ...profile, background: e.target.value })}
                                />
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="glass-card border-none shadow-2xl relative overflow-hidden bg-blue-500/5 border-blue-500/20">
                        <CardHeader className="p-6 border-b border-blue-500/10">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-blue-500/10 rounded-xl">
                                        <svg viewBox="0 0 24 24" className="h-5 w-5 fill-blue-500" xmlns="http://www.w3.org/2000/svg"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" /></svg>
                                    </div>
                                    <CardTitle className="text-lg font-bold">X (Twitter) 連携</CardTitle>
                                </div>
                                {xAccount && (
                                    <div className="flex items-center gap-1 bg-green-500/10 text-green-600 dark:text-green-400 px-2 py-1 rounded-full text-[10px] font-bold tracking-tight">
                                        <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                                        CONNECTED
                                    </div>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="p-6">
                            {xAccount ? (
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="h-10 w-10 rounded-full bg-blue-500/10 flex items-center justify-center font-bold text-blue-500">
                                            {xAccount.screenName?.[0]?.toUpperCase()}
                                        </div>
                                        <div>
                                            <p className="font-bold text-sm">@{xAccount.screenName}</p>
                                            <p className="text-[10px] text-muted-foreground tracking-tighter uppercase font-medium">Automatic posting enabled</p>
                                        </div>
                                    </div>
                                    <Button variant="outline" size="sm" onClick={handleDisconnectX} className="text-red-500 hover:text-red-600 hover:bg-red-50 border-red-200 rounded-lg h-8 px-3 text-xs">
                                        連携解除
                                    </Button>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    <p className="text-sm text-muted-foreground leading-snug">
                                        アカウントを連携すると、生成された投稿を指定時間に自動で公開できるようになります。
                                    </p>
                                    <Button onClick={handleConnectX} className="w-full bg-black hover:bg-black/90 text-white rounded-xl h-11 font-bold transition-all shadow-lg active:scale-[0.98]">
                                        Xアカウントと連携する
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <Card className="glass-card border-none shadow-2xl relative overflow-hidden bg-indigo-500/5 border-indigo-500/20">
                        <CardHeader className="p-6 border-b border-indigo-500/10">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-indigo-500/10 rounded-xl">
                                    <Zap className="h-5 w-5 text-indigo-500" />
                                </div>
                                <CardTitle className="text-lg font-bold">下書き配信設定 (Discord / Telegram)</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="p-6 space-y-4">
                            <div className="space-y-2">
                                <Label className="text-xs font-bold text-muted-foreground uppercase">Discord Webhook URL</Label>
                                <Input
                                    placeholder="https://discord.com/api/webhooks/..."
                                    value={profile.discordWebhookUrl || ""}
                                    onChange={(e) => setProfile({ ...profile, discordWebhookUrl: e.target.value })}
                                    className="bg-white/50 dark:bg-black/20"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-xs font-bold text-muted-foreground uppercase">Telegram Bot Token</Label>
                                <Input
                                    placeholder="12345678:ABCDEF..."
                                    value={profile.telegramBotToken || ""}
                                    onChange={(e) => setProfile({ ...profile, telegramBotToken: e.target.value })}
                                    className="bg-white/50 dark:bg-black/20"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-xs font-bold text-muted-foreground uppercase">Telegram Chat ID</Label>
                                <Input
                                    placeholder="例: -100123456789"
                                    value={profile.telegramChatId || ""}
                                    onChange={(e) => setProfile({ ...profile, telegramChatId: e.target.value })}
                                    className="bg-white/50 dark:bg-black/20"
                                />
                            </div>
                            <p className="text-[10px] text-muted-foreground leading-relaxed italic">
                                ※X APIの仕様変更により、自動投稿にはクレジットカード登録が必要です。
                                無料で運用する場合は、ここに下書き用チャンネルを設定し、届いた文章をコピペして手動で投稿してください。
                            </p>
                        </CardContent>
                    </Card>
                </div>
            </div>

            <div className="p-10 glass-card bg-primary/5 border-primary/10 rounded-[32px] relative overflow-hidden shadow-inner">
                <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
                    <div className="space-y-3 max-w-xl text-center md:text-left">
                        <div className="flex items-center gap-2 justify-center md:justify-start">
                            <Feather className="h-5 w-5 text-primary" />
                            <h3 className="text-xl font-black italic">Perfectly Synchronized</h3>
                        </div>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                            「ここで入力された情報は、AI投稿生成時のプロンプトに動的に組み込まれます。
                            これにより、AIっぽさを排除した『あなたならでは』の独自の視点を持つ文章が生成されるようになります。」
                        </p>
                    </div>
                    <Button
                        onClick={handleSave}
                        disabled={saving}
                        className="premium-button px-12 py-8 rounded-2xl text-lg group w-full md:w-auto"
                    >
                        {saving ? (
                            <Loader2 className="h-6 w-6 animate-spin" />
                        ) : (
                            <>
                                <Save className="mr-3 h-5 w-5" />
                                プロフィールを同期する
                                <ChevronRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                            </>
                        )}
                    </Button>
                </div>

                {/* Background decorative elements */}
                <div className="absolute -bottom-24 -left-20 h-64 w-64 bg-primary/5 rounded-full blur-3xl" />
                <div className="absolute -top-24 -right-20 h-64 w-64 bg-primary/10 rounded-full blur-3xl" />
            </div>
        </div>
    )
}

