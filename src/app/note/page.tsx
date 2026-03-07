"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import {
    Loader2, BookOpen, Copy, Download, Sparkles,
    FileText, Clock, Tag, ChevronRight, Image as ImageIcon
} from "lucide-react"

interface NoteArticle {
    title: string;
    subtitle: string;
    headerImagePrompt: string;
    content: string;
    readingTime: number;
    tags: string[];
}

export default function NotePage() {
    const [topic, setTopic] = useState("")
    const [targetLength, setTargetLength] = useState("medium")
    const [generating, setGenerating] = useState(false)
    const [article, setArticle] = useState<NoteArticle | null>(null)
    const [profile, setProfile] = useState<any>(null)
    const [activeTab, setActiveTab] = useState<"preview" | "markdown">("preview")
    const [charCount, setCharCount] = useState(0)

    useEffect(() => {
        fetch("/api/profile").then(r => r.json()).then(d => {
            if (d.success && d.profile) setProfile(d.profile)
        })
    }, [])

    useEffect(() => {
        if (article?.content) {
            // Markdownの記号を除いた大まかな文字数
            const text = article.content.replace(/[#*`>\-\[\]()!|]/g, '').replace(/\n+/g, '\n')
            setCharCount(text.length)
        }
    }, [article])

    const handleGenerate = async () => {
        if (!topic.trim()) {
            toast.error("テーマを入力してください")
            return
        }
        setGenerating(true)
        setArticle(null)
        try {
            const res = await fetch("/api/note", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ topic, targetLength, profile })
            })
            const data = await res.json()
            if (data.success) {
                setArticle(data.article)
                toast.success("note記事を生成しました！")
            } else {
                toast.error("生成に失敗しました: " + data.error)
            }
        } catch (error) {
            toast.error("サーバーエラーが発生しました")
        } finally {
            setGenerating(false)
        }
    }

    const copyToClipboard = (text: string, label: string) => {
        navigator.clipboard.writeText(text)
        toast.success(`${label}をコピーしました`)
    }

    const renderMarkdown = (md: string) => {
        return md
            .replace(/^### (.+)$/gm, '<h3 class="text-lg font-bold mt-6 mb-2 text-foreground">$1</h3>')
            .replace(/^## (.+)$/gm, '<h2 class="text-xl font-extrabold mt-8 mb-3 text-foreground border-b border-border/30 pb-2">$1</h2>')
            .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-extrabold mt-6 mb-4 premium-gradient-text">$1</h1>')
            .replace(/\*\*(.+?)\*\*/g, '<strong class="font-bold text-foreground">$1</strong>')
            .replace(/`(.+?)`/g, '<code class="bg-primary/10 text-primary px-1.5 py-0.5 rounded text-sm font-mono">$1</code>')
            .replace(/^- (.+)$/gm, '<li class="ml-4 mb-1 text-muted-foreground list-disc">$1</li>')
            .replace(/^> (.+)$/gm, '<blockquote class="border-l-4 border-primary/40 pl-4 italic text-muted-foreground my-3">$1</blockquote>')
            .replace(/^(\d+)\. (.+)$/gm, '<li class="ml-4 mb-1 text-muted-foreground list-decimal">$2</li>')
            .replace(/\n\n/g, '</p><p class="mb-4 leading-relaxed text-muted-foreground">')
            .replace(/\n/g, '<br />')
    }

    return (
        <div className="space-y-10 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex flex-col space-y-2">
                <h1 className="text-4xl font-extrabold tracking-tight">
                    note記事を <span className="premium-gradient-text">AI生成</span> する
                </h1>
                <p className="text-muted-foreground text-lg">
                    5,000〜10,000文字の超高密度・有料級note記事を一発生成。
                </p>
            </div>

            {/* 生成フォーム */}
            <Card className="glass-card border-none shadow-2xl">
                <CardHeader className="p-8 border-b border-border/10">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-primary/10 rounded-2xl">
                            <BookOpen className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                            <CardTitle className="text-xl font-bold">記事設定</CardTitle>
                            <p className="text-xs text-muted-foreground mt-1">テーマと文字数を指定してください</p>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-8 space-y-6">
                    <div className="space-y-3">
                        <Label className="text-xs font-black uppercase tracking-widest text-muted-foreground">
                            記事テーマ・キーワード
                        </Label>
                        <Textarea
                            placeholder="例: ChatGPTを使って月収を3倍にした具体的な方法、AIエージェントの2025年最新活用術..."
                            value={topic}
                            onChange={e => setTopic(e.target.value)}
                            className="min-h-[100px] bg-white/50 dark:bg-black/20 border-border/50 rounded-xl font-medium leading-relaxed"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-6">
                        <div className="space-y-3">
                            <Label className="text-xs font-black uppercase tracking-widest text-muted-foreground">
                                文字数
                            </Label>
                            <Select value={targetLength} onValueChange={setTargetLength}>
                                <SelectTrigger className="h-12 bg-white/50 dark:bg-black/20 border-border/50 rounded-xl">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="medium">標準（5,000〜7,000文字）</SelectItem>
                                    <SelectItem value="long">ロング（8,000〜10,000文字）</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-3">
                            <Label className="text-xs font-black uppercase tracking-widest text-muted-foreground">
                                プロフィール反映
                            </Label>
                            <div className="h-12 flex items-center px-4 bg-white/30 dark:bg-black/10 rounded-xl border border-border/30 text-sm text-muted-foreground">
                                {profile?.accountName ? `✅ ${profile.accountName}` : '⚠️ プロフィール未設定'}
                            </div>
                        </div>
                    </div>

                    <Button
                        onClick={handleGenerate}
                        disabled={generating || !topic.trim()}
                        className="premium-button w-full py-8 rounded-2xl text-lg group"
                    >
                        {generating ? (
                            <>
                                <Loader2 className="mr-3 h-5 w-5 animate-spin" />
                                AI執筆中... 少々お待ちください（1〜2分）
                            </>
                        ) : (
                            <>
                                <Sparkles className="mr-3 h-5 w-5" />
                                超高密度note記事を生成する
                                <ChevronRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                            </>
                        )}
                    </Button>
                </CardContent>
            </Card>

            {/* 生成結果 */}
            {article && (
                <div className="space-y-6">
                    {/* 記事メタ情報 */}
                    <Card className="glass-card border-none shadow-xl overflow-hidden">
                        <CardContent className="p-8">
                            <div className="space-y-3">
                                <h2 className="text-2xl font-extrabold leading-tight">{article.title}</h2>
                                <p className="text-muted-foreground">{article.subtitle}</p>
                                <div className="flex flex-wrap gap-3 pt-2">
                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/40 px-3 py-1.5 rounded-full">
                                        <FileText className="h-3 w-3" />
                                        約{charCount.toLocaleString()}文字
                                    </div>
                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/40 px-3 py-1.5 rounded-full">
                                        <Clock className="h-3 w-3" />
                                        約{article.readingTime}分で読める
                                    </div>
                                    {article.tags?.map(tag => (
                                        <div key={tag} className="flex items-center gap-1 text-xs text-primary bg-primary/10 px-2.5 py-1 rounded-full">
                                            <Tag className="h-2.5 w-2.5" />
                                            {tag}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* 画像プロンプト */}
                    {article.headerImagePrompt && (
                        <Card className="glass-card border-none shadow-xl bg-blue-500/5 border-blue-500/10">
                            <CardContent className="p-6">
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <ImageIcon className="h-4 w-4 text-blue-500" />
                                            <span className="text-xs font-bold text-blue-500 uppercase tracking-wider">AIヘッダー画像プロンプト</span>
                                        </div>
                                        <p className="text-sm text-muted-foreground font-mono leading-relaxed">{article.headerImagePrompt}</p>
                                    </div>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => copyToClipboard(article.headerImagePrompt, "画像プロンプト")}
                                        className="flex-shrink-0 rounded-lg border-blue-200 hover:bg-blue-50"
                                    >
                                        <Copy className="h-3 w-3 mr-1" />コピー
                                    </Button>
                                </div>
                                <p className="text-[10px] text-muted-foreground mt-3 opacity-60">
                                    ※ このプロンプトをMidjourney / FLUX / Adobe Fireflyに貼り付けてヘッダー画像を生成してください
                                </p>
                            </CardContent>
                        </Card>
                    )}

                    {/* プレビュー / Markdownタブ */}
                    <Card className="glass-card border-none shadow-2xl overflow-hidden">
                        <CardHeader className="p-6 border-b border-border/10">
                            <div className="flex items-center justify-between">
                                <div className="flex gap-2">
                                    <Button
                                        variant={activeTab === "preview" ? "default" : "ghost"}
                                        size="sm"
                                        onClick={() => setActiveTab("preview")}
                                        className="rounded-lg"
                                    >
                                        プレビュー
                                    </Button>
                                    <Button
                                        variant={activeTab === "markdown" ? "default" : "ghost"}
                                        size="sm"
                                        onClick={() => setActiveTab("markdown")}
                                        className="rounded-lg"
                                    >
                                        Markdown
                                    </Button>
                                </div>
                                <Button
                                    onClick={() => copyToClipboard(article.content, "記事本文")}
                                    className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl h-9 px-4 text-sm font-bold"
                                >
                                    <Copy className="h-3.5 w-3.5 mr-2" />
                                    note.comにコピペ
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent className="p-8">
                            {activeTab === "preview" ? (
                                <div
                                    className="prose prose-sm max-w-none leading-relaxed"
                                    dangerouslySetInnerHTML={{
                                        __html: `<p class="mb-4 leading-relaxed text-muted-foreground">${renderMarkdown(article.content)}</p>`
                                    }}
                                />
                            ) : (
                                <Textarea
                                    value={article.content}
                                    readOnly
                                    className="min-h-[600px] font-mono text-sm bg-black/20 border-border/30 rounded-xl"
                                />
                            )}
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    )
}
