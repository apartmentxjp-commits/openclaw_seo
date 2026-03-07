"use client"

import { Inter } from 'next/font/google';
import './globals.css';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Toaster } from "@/components/ui/sonner"
import {
  LayoutDashboard,
  PenTool,
  Calendar as CalendarIcon,
  Clock,
  User,
  Settings,
  Sparkles,
  BookOpen,
  History
} from "lucide-react"

const inter = Inter({ subsets: ['latin'] });

const navItems = [
  { href: "/", label: "ダッシュボード", icon: LayoutDashboard },
  { href: "/posts", label: "投稿生成", icon: PenTool },
  { href: "/history", label: "投稿履歴", icon: History },
  { href: "/note", label: "note記事作成", icon: BookOpen },
  { href: "/calendar", label: "カレンダー", icon: CalendarIcon },
  { href: "/schedules", label: "投稿スケジュール", icon: Clock },
  { href: "/profile", label: "プロフィール設定", icon: User },
  { href: "/integrations", label: "連携設定", icon: Settings },
];

// モバイル用ボトムナビ（主要4項目のみ）
const mobileNavItems = [
  { href: "/", label: "Home", icon: LayoutDashboard },
  { href: "/posts", label: "生成", icon: PenTool },
  { href: "/history", label: "履歴", icon: History },
  { href: "/profile", label: "設定", icon: User },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <html lang="ja">
      <body className={`${inter.className} min-h-screen`}>
        <div className="flex h-screen overflow-hidden">
          {/* プレミアム・フローティング・サイドバー */}
          <aside className="fixed left-4 top-4 bottom-4 w-72 hidden lg:flex flex-col glass-card z-50">
            <div className="p-6 flex items-center gap-3">
              <div className="h-10 w-10 bg-primary rounded-xl flex items-center justify-center shadow-lg shadow-primary/20 animate-float">
                <Sparkles className="text-white h-6 w-6" />
              </div>
              <h2 className="text-xl font-bold tracking-tight premium-gradient-text">Auto Poster</h2>
            </div>

            <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group ${isActive
                      ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20 scale-[1.02]'
                      : 'text-muted-foreground hover:bg-white/50 dark:hover:bg-white/5 hover:text-foreground'
                      }`}
                  >
                    <Icon className={`h-5 w-5 ${isActive ? 'text-white' : 'group-hover:text-primary transition-colors'}`} />
                    <span className="font-medium">{item.label}</span>
                    {isActive && (
                      <div className="ml-auto w-1.5 h-1.5 rounded-full bg-white shadow-sm" />
                    )}
                  </Link>
                );
              })}
            </nav>

            <div className="p-4 mt-auto">
              <div className="p-4 rounded-2xl bg-gradient-to-br from-indigo-50 to-blue-50 dark:from-indigo-900/20 dark:to-blue-900/20 border border-indigo-100/50 dark:border-indigo-500/10">
                <p className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider mb-1">Status</p>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-xs font-medium">System Active</span>
                </div>
              </div>
            </div>
          </aside>

          {/* メインレイアウトの調整（サイドバーの幅を考慮） */}
          <main className="flex-1 overflow-y-auto lg:ml-[20rem] transition-all duration-500">
            <div className="container mx-auto px-6 py-8 md:px-10 max-w-7xl">
              {children}
            </div>
          </main>
        </div>
        <Toaster position="top-right" />

        {/* モバイル用ボトムナビゲーション */}
        <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden glass border-t border-border/50">
          <div className="flex justify-around items-center h-16 px-2">
            {mobileNavItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-all ${isActive ? 'text-primary' : 'text-muted-foreground'
                    }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-[10px] font-medium">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </nav>
      </body>
    </html>
  );
}
