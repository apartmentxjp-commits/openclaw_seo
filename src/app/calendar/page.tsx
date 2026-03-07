"use client"

import * as React from "react"
import { Calendar } from "@/components/ui/calendar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import {
    Loader2,
    Trash2,
    Calendar as CalendarIcon,
    Clock,
    GripVertical,
    Sparkles,
    ChevronRight,
    Plus
} from "lucide-react"

import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragEndEvent
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
    useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface PostItem {
    id: string;
    timeString: string | null;
    content: string;
    status: string;
    scheduledAt: string | null;
}

function SortableItem(props: { post: PostItem; onDelete: (id: string) => void }) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({ id: props.post.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 10 : 1,
        opacity: isDragging ? 0.8 : 1,
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'SCHEDULED':
                return <Badge className="bg-blue-500/10 text-blue-600 border-blue-200 dark:border-blue-500/20 hover:bg-blue-500/20">予約中</Badge>;
            case 'POSTED':
                return <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-200 dark:border-emerald-500/20 hover:bg-emerald-500/20">投稿済み</Badge>;
            case 'ERROR':
                return <Badge variant="destructive">エラー</Badge>;
            case 'DRAFT':
                return <Badge variant="secondary">下書き</Badge>;
            default:
                return <Badge variant="outline">{status}</Badge>;
        }
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={`group p-5 glass-card mb-4 ${isDragging ? 'ring-2 ring-primary bg-white/80 dark:bg-white/10' : ''}`}
        >
            <div className="flex justify-between items-start gap-4">
                <div className="flex items-center gap-3 overflow-hidden">
                    <div {...attributes} {...listeners} className="cursor-grab active:cursor-grabbing p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-colors">
                        <GripVertical className="h-4 w-4 text-muted-foreground/50 group-hover:text-primary transition-colors" />
                    </div>
                    <div className="space-y-1.5 min-w-0">
                        <div className="flex items-center gap-2">
                            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-white/50 dark:bg-white/5 border border-border/50 text-[10px] font-bold text-muted-foreground">
                                <Clock className="h-3 w-3" />
                                {props.post.timeString || '--:--'}
                            </div>
                            {getStatusBadge(props.post.status)}
                        </div>
                        <p className="text-sm font-medium leading-relaxed text-foreground/80 line-clamp-2">
                            {props.post.content}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-muted-foreground hover:text-red-500 transition-colors"
                        onClick={() => props.onDelete(props.post.id)}
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg">
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </Button>
                </div>
            </div>
        </div>
    );
}

export default function CalendarPage() {
    const [date, setDate] = React.useState<Date | undefined>(new Date())
    const [posts, setPosts] = React.useState<PostItem[]>([])
    const [isLoading, setIsLoading] = React.useState(true)

    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const fetchPosts = React.useCallback(async () => {
        setIsLoading(true);
        try {
            const dateStr = date ? date.toISOString().split('T')[0] : '';
            const res = await fetch(`/api/posts${dateStr ? `?date=${dateStr}` : ''}`);
            const data = await res.json();
            if (data.success) {
                setPosts(data.posts);
            }
        } catch (error) {
            toast.error("投稿の取得に失敗しました");
        } finally {
            setIsLoading(false);
        }
    }, [date]);

    React.useEffect(() => {
        fetchPosts();
    }, [fetchPosts]);

    const handleDelete = async (id: string) => {
        if (!confirm("この投稿予約を削除しますか？")) return;

        try {
            const res = await fetch(`/api/posts?id=${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.success) {
                setPosts(prev => prev.filter(p => p.id !== id));
                toast.success("削除完了しました");
            }
        } catch (error) {
            toast.error("削除中にエラーが発生しました");
        }
    };

    function handleDragEnd(event: DragEndEvent) {
        const { active, over } = event;

        if (over && active.id !== over.id) {
            setPosts((items) => {
                const oldIndex = items.findIndex((item) => item.id === active.id);
                const newIndex = items.findIndex((item) => item.id === over.id);
                return arrayMove(items, oldIndex, newIndex);
            });
            toast.info("並び替えました（時間は維持されます）");
        }
    }

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div className="space-y-1">
                    <h1 className="text-4xl font-extrabold tracking-tight">
                        <span className="premium-gradient-text">カレンダー</span> 管理
                    </h1>
                    <p className="text-muted-foreground text-lg">
                        配信スケジュールを直感的に微調整。
                    </p>
                </div>
                <Button className="premium-button group shadow-xl transition-all hover:scale-105 active:scale-95">
                    <Plus className="mr-2 h-5 w-5 group-hover:rotate-90 transition-transform duration-300" />
                    手動で投稿を作成
                </Button>
            </div>

            <div className="grid lg:grid-cols-[400px_1fr] gap-10">
                {/* 左側: プレミアムカレンダー */}
                <Card className="glass-card border-none shadow-2xl p-4 h-fit sticky top-8">
                    <CardHeader className="pb-4 items-center gap-2">
                        <div className="p-3 bg-blue-500/10 rounded-2xl">
                            <CalendarIcon className="h-6 w-6 text-blue-500" />
                        </div>
                        <CardTitle className="text-xl font-bold tracking-tight">日付を選択</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0 flex justify-center pb-4">
                        <Calendar
                            mode="single"
                            selected={date}
                            onSelect={setDate}
                            className="bg-transparent"
                            classNames={{
                                day_selected: "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground focus:bg-primary focus:text-primary-foreground rounded-xl shadow-lg shadow-primary/30",
                                day_today: "bg-accent text-accent-foreground rounded-xl font-bold border border-primary/20",
                                day: "h-11 w-11 p-0 font-medium aria-selected:opacity-100 hover:bg-primary/10 rounded-xl transition-all",
                            }}
                        />
                    </CardContent>
                </Card>

                {/* 右側: プレミアムタイムライン */}
                <div className="space-y-6">
                    <div className="flex items-center justify-between px-2">
                        <div className="flex items-center gap-3">
                            <div className="p-2.5 bg-indigo-500/10 rounded-xl">
                                <Clock className="h-5 w-5 text-indigo-500" />
                            </div>
                            <h2 className="text-2xl font-bold tracking-tight">
                                {date ? `${date.toLocaleDateString('ja-JP', { month: 'long', day: 'numeric', weekday: 'short' })}` : "日付を選択"}
                            </h2>
                        </div>
                        <Badge variant="outline" className="glass py-1 px-4 text-xs font-bold rounded-full">
                            {posts.length} 件の予約
                        </Badge>
                    </div>

                    <div className="relative min-h-[500px]">
                        {isLoading ? (
                            <div className="absolute inset-0 flex items-center justify-center">
                                <Loader2 className="h-10 w-10 animate-spin text-primary/40" />
                            </div>
                        ) : posts.length === 0 ? (
                            <div className="py-32 text-center glass-card border-none flex flex-col items-center gap-6">
                                <div className="p-6 bg-muted/50 rounded-full animate-float">
                                    <CalendarIcon className="h-12 w-12 text-muted-foreground/30" />
                                </div>
                                <div className="space-y-1">
                                    <p className="text-lg font-bold text-muted-foreground">この日の予約はありません</p>
                                    <p className="text-sm text-muted-foreground/60">AI生成ページから魔法の一括予約を開始しましょう。</p>
                                </div>
                                <Button variant="outline" className="rounded-xl px-8 border-primary/20 hover:bg-primary/5">
                                    投稿をAIで生成する
                                </Button>
                            </div>
                        ) : (
                            <DndContext
                                sensors={sensors}
                                collisionDetection={closestCenter}
                                onDragEnd={handleDragEnd}
                            >
                                <div className="space-y-1">
                                    <SortableContext
                                        items={posts.map(p => p.id)}
                                        strategy={verticalListSortingStrategy}
                                    >
                                        {posts.map((post) => (
                                            <SortableItem key={post.id} post={post} onDelete={handleDelete} />
                                        ))}
                                    </SortableContext>
                                </div>
                            </DndContext>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
