'use client'

import { useState, useEffect, useRef } from 'react'

// ── エージェント定義 ──────────────────────────────────────────────────
const AGENTS = {
  writer: {
    name: 'WriterAgent',
    role: '記事執筆',
    color: '#6366f1',
    bgColor: '#6366f115',
    borderColor: '#6366f140',
    deskLabel: 'DESK A',
  },
  scheduler: {
    name: 'Scheduler',
    role: 'スケジュール管理',
    color: '#f59e0b',
    bgColor: '#f59e0b15',
    borderColor: '#f59e0b40',
    deskLabel: 'DESK B',
  },
  analyzer: {
    name: 'AnalyticsAgent',
    role: 'アクセス分析',
    color: '#8b5cf6',
    bgColor: '#8b5cf615',
    borderColor: '#8b5cf640',
    deskLabel: 'DESK C',
  },
  optimizer: {
    name: 'OptimizerAgent',
    role: '記事最適化',
    color: '#10b981',
    bgColor: '#10b98115',
    borderColor: '#10b98140',
    deskLabel: 'DESK D',
  },
}

type AgentKey = keyof typeof AGENTS

type Thought = {
  agent: string
  thought: string
  status: string   // idle | thinking | working | success | error | stuck
  detail?: string
  ts: string
  ping?: boolean
}

// ── ステータス設定 ────────────────────────────────────────────────────
const STATUS_CONFIG: Record<string, { label: string; dotColor: string; pulse: boolean }> = {
  idle:     { label: '待機中',   dotColor: '#52525b',  pulse: false },
  thinking: { label: '考え中',   dotColor: '#f59e0b',  pulse: true  },
  working:  { label: '作業中',   dotColor: '#6366f1',  pulse: true  },
  success:  { label: '完了',     dotColor: '#22c55e',  pulse: false },
  error:    { label: 'エラー',   dotColor: '#ef4444',  pulse: false },
  stuck:    { label: '詰まり中', dotColor: '#f97316',  pulse: true  },
}

// ── エージェントアバター SVG ────────────────────────────────────────
function AgentAvatar({ color, status }: { color: string; status: string }) {
  const isWorking = status === 'working' || status === 'thinking'
  return (
    <svg width="56" height="72" viewBox="0 0 56 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* 影 */}
      <ellipse cx="28" cy="70" rx="16" ry="3" fill="#000" opacity="0.15" />
      {/* 体 */}
      <rect x="14" y="38" width="28" height="26" rx="8" fill={color} opacity="0.9" />
      {/* 腕（作業中は角度変化） */}
      <rect
        x={isWorking ? "4" : "6"}
        y={isWorking ? "36" : "40"}
        width="11" height="7" rx="3.5"
        fill={color}
        style={{ transition: 'all 0.4s ease' }}
      />
      <rect
        x={isWorking ? "41" : "39"}
        y={isWorking ? "36" : "40"}
        width="11" height="7" rx="3.5"
        fill={color}
        style={{ transition: 'all 0.4s ease' }}
      />
      {/* 首 */}
      <rect x="24" y="32" width="8" height="8" rx="2" fill={color} opacity="0.7" />
      {/* 頭 */}
      <circle cx="28" cy="22" r="16" fill={color} />
      {/* 目（作業中は点滅） */}
      <circle cx="22" cy="20" r="2.5" fill="white" opacity={isWorking ? 0.9 : 0.7} />
      <circle cx="34" cy="20" r="2.5" fill="white" opacity={isWorking ? 0.9 : 0.7} />
      {/* 瞳 */}
      <circle cx={isWorking ? "23" : "22"} cy="20" r="1.2" fill="#111" />
      <circle cx={isWorking ? "35" : "34"} cy="20" r="1.2" fill="#111" />
      {/* 口（成功時は笑顔、エラー時は困り顔） */}
      {status === 'success' ? (
        <path d="M23 27 Q28 31 33 27" stroke="white" strokeWidth="1.5" strokeLinecap="round" fill="none" opacity="0.8" />
      ) : status === 'error' ? (
        <path d="M23 29 Q28 26 33 29" stroke="white" strokeWidth="1.5" strokeLinecap="round" fill="none" opacity="0.6" />
      ) : (
        <rect x="23" y="27" width="10" height="1.5" rx="0.75" fill="white" opacity="0.5" />
      )}
    </svg>
  )
}

// ── 吹き出しコンポーネント ───────────────────────────────────────────
function ThoughtBubble({
  thought,
  detail,
  status,
  color,
  flash,
}: {
  thought: string
  detail?: string
  status: string
  color: string
  flash: boolean
}) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.idle
  return (
    <div
      className="relative"
      style={{
        animation: flash ? 'bubble-pop 0.35s cubic-bezier(0.34,1.56,0.64,1)' : 'none',
      }}
    >
      {/* 本体 */}
      <div
        className="rounded-2xl rounded-bl-sm px-3 py-2.5 max-w-[200px] min-w-[140px] shadow-lg"
        style={{
          background: '#1c1c20',
          border: `1.5px solid ${color}50`,
          boxShadow: `0 4px 20px ${color}15`,
        }}
      >
        {/* ステータスバッジ */}
        <div className="flex items-center gap-1.5 mb-1.5">
          <span
            className="w-1.5 h-1.5 rounded-full flex-shrink-0"
            style={{
              background: cfg.dotColor,
              boxShadow: cfg.pulse ? `0 0 6px ${cfg.dotColor}` : 'none',
              animation: cfg.pulse ? 'status-pulse 1.5s ease-in-out infinite' : 'none',
            }}
          />
          <span className="text-[9px] font-medium uppercase tracking-wider" style={{ color: cfg.dotColor }}>
            {cfg.label}
          </span>
        </div>

        {/* 思考テキスト */}
        <p className="text-[11px] leading-snug text-[#e4e4e7] font-medium">
          {thought}
        </p>

        {/* 詳細（グレー小文字） */}
        {detail && (
          <p className="text-[9px] text-[#71717a] mt-1 leading-tight">
            {detail}
          </p>
        )}
      </div>

      {/* 吹き出しの尻尾 */}
      <div
        className="absolute left-4 -bottom-2 w-0 h-0"
        style={{
          borderLeft: '6px solid transparent',
          borderRight: '6px solid transparent',
          borderTop: `8px solid ${color}50`,
        }}
      />
      <div
        className="absolute left-[17px] -bottom-[6px] w-0 h-0"
        style={{
          borderLeft: '5px solid transparent',
          borderRight: '5px solid transparent',
          borderTop: '7px solid #1c1c20',
        }}
      />
    </div>
  )
}

// ── モニター（デスクのPC画面）────────────────────────────────────────
function Monitor({ color, status }: { color: string; status: string }) {
  const isActive = status === 'working' || status === 'thinking'
  return (
    <div className="flex flex-col items-center">
      {/* 画面 */}
      <div
        className="w-20 h-13 rounded-t-md border-2 flex items-center justify-center overflow-hidden"
        style={{ borderColor: color + '60', background: '#0d0d10' }}
      >
        {isActive ? (
          // タイピングアニメーション
          <div className="w-full px-2 space-y-1">
            {[0.2, 0.5, 0.3, 0.7].map((w, i) => (
              <div
                key={i}
                className="h-0.5 rounded-full"
                style={{
                  background: color,
                  width: `${w * 100}%`,
                  opacity: 0.6,
                  animation: `type-line 1.4s ${i * 0.2}s ease-in-out infinite`,
                }}
              />
            ))}
          </div>
        ) : (
          <div className="text-[10px] text-[#3f3f46] font-mono">---</div>
        )}
      </div>
      {/* スタンド */}
      <div className="w-4 h-2" style={{ background: '#27272a' }} />
      <div className="w-10 h-1 rounded" style={{ background: '#27272a' }} />
    </div>
  )
}

// ── デスクカード ─────────────────────────────────────────────────────
function DeskCard({
  agentKey,
  thought,
  flash,
}: {
  agentKey: AgentKey
  thought: Thought | null
  flash: boolean
}) {
  const agent = AGENTS[agentKey]
  const status = thought?.status ?? 'idle'

  return (
    <div
      className="relative flex flex-col items-center gap-2 p-4 pt-6 rounded-2xl border transition-all duration-500"
      style={{
        background: agent.bgColor,
        borderColor: status === 'idle' ? agent.borderColor : agent.color + '60',
        boxShadow: status !== 'idle' ? `0 0 30px ${agent.color}20, inset 0 1px 0 ${agent.color}15` : 'none',
      }}
    >
      {/* デスクラベル */}
      <div
        className="absolute top-2 left-3 text-[9px] font-bold tracking-[0.2em]"
        style={{ color: agent.color + '80' }}
      >
        {agent.deskLabel}
      </div>

      {/* 吹き出し */}
      {thought && (
        <ThoughtBubble
          thought={thought.thought}
          detail={thought.detail ?? undefined}
          status={status}
          color={agent.color}
          flash={flash}
        />
      )}

      {/* アバター */}
      <AgentAvatar color={agent.color} status={status} />

      {/* モニター */}
      <Monitor color={agent.color} status={status} />

      {/* デスク天板 */}
      <div
        className="w-full h-3 rounded-t-sm mt-1"
        style={{ background: '#1e1e24', borderTop: `2px solid ${agent.color}30` }}
      />

      {/* 名前・役割 */}
      <div className="text-center mt-1">
        <p className="text-xs font-semibold" style={{ color: agent.color }}>
          {agent.name}
        </p>
        <p className="text-[9px] text-[#52525b] mt-0.5">{agent.role}</p>
      </div>
    </div>
  )
}

// ── アクティビティストリーム ─────────────────────────────────────────
function ActivityStream({ logs }: { logs: Thought[] }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight
    }
  }, [logs])

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-[#27272a] flex items-center justify-between">
        <p className="text-xs font-semibold text-[#a1a1aa] tracking-wider uppercase">Activity Feed</p>
        <span className="text-[9px] font-mono text-[#52525b]">{logs.length} events</span>
      </div>
      <div ref={ref} className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5">
        {logs.length === 0 && (
          <p className="text-[11px] text-[#3f3f46] text-center mt-8">接続待機中...</p>
        )}
        {logs.map((log, i) => {
          const agent = AGENTS[log.agent as AgentKey]
          const cfg = STATUS_CONFIG[log.status] ?? STATUS_CONFIG.idle
          return (
            <div
              key={i}
              className="flex gap-2 py-1.5 px-2 rounded-lg hover:bg-[#18181b] transition-colors"
              style={{ animation: i === logs.length - 1 ? 'fade-in 0.3s ease' : 'none' }}
            >
              {/* カラードット */}
              <div
                className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1"
                style={{ background: agent?.color ?? '#52525b' }}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className="text-[9px] font-semibold" style={{ color: agent?.color ?? '#71717a' }}>
                    {agent?.name ?? log.agent}
                  </span>
                  <span
                    className="text-[8px] px-1 py-0.5 rounded"
                    style={{ background: cfg.dotColor + '20', color: cfg.dotColor }}
                  >
                    {cfg.label}
                  </span>
                  <span className="text-[8px] text-[#3f3f46] ml-auto font-mono">
                    {new Date(log.ts).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                </div>
                <p className="text-[10px] text-[#a1a1aa] leading-snug truncate">{log.thought}</p>
                {log.detail && (
                  <p className="text-[9px] text-[#52525b] truncate">{log.detail}</p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── メインページ ─────────────────────────────────────────────────────
export default function OfficePage() {
  const [thoughts, setThoughts] = useState<Record<string, Thought>>({})
  const [activityLog, setActivityLog] = useState<Thought[]>([])
  const [flashMap, setFlashMap] = useState<Record<string, boolean>>({})
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const es = new EventSource('/api/thoughts/stream')

    es.onopen = () => setConnected(true)
    es.onerror = () => setConnected(false)

    es.onmessage = (e) => {
      const data: Thought = JSON.parse(e.data)
      if (data.ping) return

      // 最新状態を更新
      setThoughts((prev) => ({ ...prev, [data.agent]: data }))

      // アクティビティログに追加（最大100件）
      setActivityLog((prev) => {
        const next = [...prev, data]
        return next.slice(-100)
      })

      // 吹き出しアニメーション
      setFlashMap((prev) => ({ ...prev, [data.agent]: true }))
      setTimeout(() => {
        setFlashMap((prev) => ({ ...prev, [data.agent]: false }))
      }, 400)
    }

    return () => es.close()
  }, [])

  const agentKeys = Object.keys(AGENTS) as AgentKey[]

  return (
    <div className="h-screen flex flex-col bg-[#09090b] overflow-hidden">

      {/* CSS アニメーション定義 */}
      <style>{`
        @keyframes bubble-pop {
          0%   { transform: scale(0.85); opacity: 0.5; }
          60%  { transform: scale(1.05); }
          100% { transform: scale(1);    opacity: 1; }
        }
        @keyframes status-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.4; transform: scale(0.7); }
        }
        @keyframes type-line {
          0%, 100% { opacity: 0.2; transform: scaleX(0.6); transform-origin: left; }
          50%      { opacity: 0.8; transform: scaleX(1); }
        }
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes room-glow {
          0%, 100% { opacity: 0.4; }
          50%      { opacity: 0.6; }
        }
      `}</style>

      {/* ヘッダー */}
      <header className="border-b border-[#27272a] bg-[#111113] px-5 h-12 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <a href="/admin" className="text-[#52525b] hover:text-[#a1a1aa] text-xs transition-colors">
            ← ダッシュボード
          </a>
          <span className="text-[#27272a]">/</span>
          <span className="text-sm font-semibold">オフィス ライブビュー</span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{
              background: connected ? '#22c55e' : '#ef4444',
              boxShadow: connected ? '0 0 6px #22c55e' : 'none',
              animation: connected ? 'status-pulse 2s ease-in-out infinite' : 'none',
            }}
          />
          <span className="text-[10px] text-[#71717a]">
            {connected ? 'LIVE' : 'DISCONNECTED'}
          </span>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">

        {/* オフィスフロア */}
        <div className="flex-1 relative overflow-hidden">

          {/* 天井照明エフェクト */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: 'radial-gradient(ellipse 60% 40% at 50% 0%, #1a1a2e30 0%, transparent 70%)',
              animation: 'room-glow 4s ease-in-out infinite',
            }}
          />

          {/* フロアタイル風グリッド */}
          <div
            className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage: `
                linear-gradient(#fff 1px, transparent 1px),
                linear-gradient(90deg, #fff 1px, transparent 1px)
              `,
              backgroundSize: '60px 60px',
            }}
          />

          {/* 会社名プレート */}
          <div className="absolute top-4 left-1/2 -translate-x-1/2 text-center">
            <p className="text-[10px] text-[#3f3f46] tracking-[0.3em] uppercase font-medium">
              OpenClaw AI Office
            </p>
          </div>

          {/* 4つのデスク — 2×2 グリッド */}
          <div className="absolute inset-0 flex items-center justify-center p-6 pt-10">
            <div className="grid grid-cols-2 gap-5 w-full max-w-2xl">
              {agentKeys.map((key) => (
                <DeskCard
                  key={key}
                  agentKey={key}
                  thought={thoughts[key] ?? null}
                  flash={flashMap[key] ?? false}
                />
              ))}
            </div>
          </div>

          {/* フロア下部のコーヒーマシン・植物装飾 */}
          <div className="absolute bottom-4 right-6 flex items-end gap-4 opacity-30">
            {/* コーヒーマシン */}
            <svg width="24" height="32" viewBox="0 0 24 32" fill="none">
              <rect x="4" y="8" width="16" height="20" rx="3" fill="#27272a" />
              <rect x="7" y="4" width="10" height="6" rx="2" fill="#3f3f46" />
              <circle cx="12" cy="20" r="4" fill="#18181b" />
              <circle cx="12" cy="20" r="2" fill="#8b5cf6" opacity="0.5" />
            </svg>
            {/* 植物 */}
            <svg width="20" height="36" viewBox="0 0 20 36" fill="none">
              <rect x="7" y="28" width="6" height="8" rx="2" fill="#3f3f46" />
              <ellipse cx="10" cy="20" rx="8" ry="12" fill="#14532d" opacity="0.7" />
              <ellipse cx="6" cy="16" rx="5" ry="8" fill="#15803d" opacity="0.6" />
              <ellipse cx="14" cy="16" rx="5" ry="8" fill="#15803d" opacity="0.6" />
            </svg>
          </div>
        </div>

        {/* アクティビティフィード（右サイド） */}
        <div
          className="w-72 flex-shrink-0 border-l border-[#27272a] bg-[#111113] flex flex-col"
        >
          <ActivityStream logs={activityLog} />
        </div>

      </div>
    </div>
  )
}
