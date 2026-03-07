"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, Twitter, MessageSquare, ExternalLink, RefreshCw, Trash2, ShieldCheck, Sparkles, ChevronRight } from "lucide-react"
import { toast } from "sonner"

interface SnsAccount {
    id: string;
    platform: string;
    screenName: string | null;
    createdAt: string;
}

export default function IntegrationsPage() {
    const [loading, setLoading] = useState(true)
    const [accounts, setAccounts] = useState<SnsAccount[]>([])
    const [isLinking, setIsLinking] = useState(false)
    const [isChecking, setIsChecking] = useState(false)
    const [isTesting, setIsTesting] = useState(false)

    useEffect(() => {
        const fetchAccounts = async () => {
            try {
                const res = await fetch("/api/accounts")
                const data = await res.json()
                if (data.success) {
                    setAccounts(data.accounts)
                }
            } catch (error) {
                console.error("Failed to fetch accounts:", error)
            } finally {
                setLoading(false)
            }
        }
        fetchAccounts()
    }, [])

    const handleLinkX = async () => {
        setIsLinking(true)
        try {
            const res = await fetch("/api/auth/x");
            const data = await res.json();
            if (data.success && data.url) {
                window.location.href = data.url;
            } else {
                toast.error(data.error || "連携URLの取得に失敗しました");
            }
        } catch (error) {
            toast.error("連携に失敗しました");
        } finally {
            setIsLinking(false);
        }
    }

    const handleRunCron = async () => {
        setIsChecking(true);
        try {
            const res = await fetch("/api/cron");
            const data = await res.json();
            if (data.success) {
                toast.success(`チェック完了: ${data.processedCount}件の投稿を処理しました`);
            } else {
                toast.error(data.error || "チェック中にエラーが発生しました");
            }
        } catch (error) {
            toast.error("実行に失敗しました");
        } finally {
            setIsChecking(false);
        }
    }

    const handleTestPost = async () => {
        setIsTesting(true);
        try {
            toast.info("テスト投稿機能を準備中...");
        } finally {
            setIsTesting(false);
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
                    世界と <span className="premium-gradient-text">コネクト</span> する
                </h1>
                <p className="text-muted-foreground text-lg">
                    SNSアカウントを連携して、あなたの声を瞬時に世界へ届けましょう。
                </p>
            </div>

            <div className="grid gap-8 md:grid-cols-2">
                {/* X (Twitter) */}
                <Card className="glass-card border-none shadow-2xl relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-6">
                        <Twitter className="h-20 w-20 text-blue-400 opacity-5 group-hover:scale-110 group-hover:rotate-12 transition-transform duration-700" />
                    </div>
                    <CardHeader className="p-8">
                        <div className="flex items-center gap-4 mb-2">
                            <div className="p-3 bg-blue-500/10 rounded-2xl">
                                <Twitter className="h-6 w-6 text-[#1DA1F2]" />
                            </div>
                            <div>
                                <CardTitle className="text-2xl font-bold">X (Twitter)</CardTitle>
                                <Badge variant="secondary" className="mt-1 bg-[#1DA1F2]/10 text-[#1DA1F2] border-none font-bold">Main Channel</Badge>
                            </div>
                        </div>
                        <CardDescription className="text-base leading-relaxed">
                            投稿の自動送信、予約投稿の実行に必要です。高機能なX API (V2) を使用します。
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="px-8 pb-8 space-y-6">
                        {accounts.some(a => a.platform === "X") ? (
                            <div className="flex items-center justify-between p-4 glass rounded-2xl border border-emerald-500/20 bg-emerald-500/5">
                                <div className="flex items-center gap-3">
                                    <div className="h-10 w-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                                        <ShieldCheck className="h-5 w-5 text-emerald-600" />
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="font-bold text-foreground">@{accounts.find(a => a.platform === "X")?.screenName}</span>
                                        <span className="text-[10px] uppercase tracking-widest text-emerald-600 font-black">Linked Now</span>
                                    </div>
                                </div>
                                <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl text-muted-foreground hover:text-red-500 hover:bg-red-50 transition-colors">
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>
                        ) : (
                            <div className="py-4 px-1">
                                <p className="text-sm text-muted-foreground italic">※ アカウントはまだ連携されていません</p>
                            </div>
                        )}

                        <Button
                            onClick={handleLinkX}
                            className="w-full bg-[#1DA1F2] hover:bg-[#1DA1F2]/90 text-white shadow-lg shadow-blue-500/20 py-7 text-lg rounded-2xl group"
                            disabled={isLinking}
                        >
                            {isLinking ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <Twitter className="mr-2 h-5 w-5" />}
                            {accounts.some(a => a.platform === "X") ? "アカウントを再連携する" : "連携を開始する"}
                            <ChevronRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                        </Button>

                        {accounts.some(a => a.platform === "X") && (
                            <div className="pt-4 border-t border-primary/5 space-y-4">
                                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Posting Controls</p>
                                <div className="grid grid-cols-2 gap-4">
                                    <Button
                                        variant="outline"
                                        onClick={handleRunCron}
                                        disabled={isChecking}
                                        className="rounded-xl border-primary/10 hover:bg-primary/5 h-12"
                                    >
                                        {isChecking ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                                        今すぐ実行
                                    </Button>
                                    <Button
                                        variant="outline"
                                        onClick={handleTestPost}
                                        disabled={isTesting}
                                        className="rounded-xl border-primary/10 hover:bg-primary/5 h-12"
                                    >
                                        {isTesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <ExternalLink className="mr-2 h-4 w-4" />}
                                        テスト投稿
                                    </Button>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Threads */}
                <Card className="glass-card border-none shadow-xl relative overflow-hidden opacity-80 group grayscale hover:grayscale-0 transition-all duration-500">
                    <CardHeader className="p-8">
                        <div className="flex items-center gap-4 mb-2">
                            <div className="p-3 bg-black/10 dark:bg-white/10 rounded-2xl">
                                <MessageSquare className="h-6 w-6 text-black dark:text-white" />
                            </div>
                            <div className="flex-1">
                                <div className="flex items-center gap-2">
                                    <CardTitle className="text-2xl font-bold">Threads</CardTitle>
                                    <Badge variant="outline" className="text-[10px] font-black uppercase tracking-tighter glass">Upcoming</Badge>
                                </div>
                            </div>
                        </div>
                        <CardDescription className="text-base leading-relaxed">
                            Metaの最新プラットフォーム。Threads APIの一般公開に合わせて連携を予定しています。
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="px-8 pb-8">
                        <Button disabled variant="outline" className="w-full border-dashed py-7 rounded-2xl text-muted-foreground bg-muted/20">
                            準備中（近日公開予定）
                        </Button>
                    </CardContent>
                </Card>
            </div>

            <div className="mt-12">
                <Card className="glass p-8 border-none ring-1 ring-primary/10 shadow-lg">
                    <div className="flex items-start gap-4">
                        <div className="p-3 bg-amber-500/10 rounded-2xl">
                            <ShieldCheck className="h-6 w-6 text-amber-500" />
                        </div>
                        <div className="space-y-4">
                            <CardTitle className="text-xl font-bold">セキュアな連携への取り組み</CardTitle>
                            <div className="grid md:grid-cols-2 gap-6 text-sm text-muted-foreground leading-relaxed">
                                <div className="space-y-2">
                                    <p className="flex items-center gap-2 font-medium text-foreground">
                                        <Sparkles className="h-3 w-3 text-primary" />
                                        API Key Management
                                    </p>
                                    <p>開発者ポータルで取得したClient ID/Secretを使用し、あなたの環境だけで完結するセキュアな設計を採用しています。</p>
                                </div>
                                <div className="space-y-2">
                                    <p className="flex items-center gap-2 font-medium text-foreground">
                                        <Sparkles className="h-3 w-3 text-primary" />
                                        OAuth 2.0 PKCE
                                    </p>
                                    <p>パスワードを保持せず、アクセストークンによる認証のみを行う最新（PKCE対応）のセキュリティ標準に準拠しています。</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    )
}
