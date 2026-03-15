'use client'

import { useState, useEffect, useRef } from 'react'

// ─────────────────────────────── Types ───────────────────────────────────────
type Thought = {
  agent: string
  thought: string
  status: string
  detail?: string
  ts: string
  ping?: boolean
}

type Walker = {
  agentKey: string
  color: string
  pos: { x: number; y: number }
  hasDoc: boolean
  phase: 'to' | 'submit' | 'back'
}

// ─────────────────────────────── Config ──────────────────────────────────────

// SEO部門 agents (live SSE from openclaw backend)
// Akiya部門 agents (simulated — separate Vercel project, no persistent process)
const AGENTS: Record<string, {
  name: string; role: string; color: string; dept: 'seo' | 'akiya' | 'mgr'
}> = {
  // SEO部門
  writer:     { name: 'WriterAgent',    role: '記事執筆',      color: '#818cf8', dept: 'seo' },
  analyzer:   { name: 'AnalyticsAgent', role: 'アクセス分析',  color: '#a78bfa', dept: 'seo' },
  optimizer:  { name: 'OptimizerAgent', role: '記事最適化',    color: '#34d399', dept: 'seo' },
  // 空き家部門
  enhancer:   { name: 'EnhanceAgent',   role: '物件AI強化',    color: '#fbbf24', dept: 'akiya' },
  uploader:   { name: 'UploadAgent',    role: 'CSV一括登録',   color: '#f97316', dept: 'akiya' },
  translator: { name: 'TranslateAgent', role: '英語自動翻訳',  color: '#fb923c', dept: 'akiya' },
  // 管理職
  scheduler:  { name: 'Scheduler',      role: '部長',          color: '#cbd5e1', dept: 'mgr' },
}

// Positions as % of office floor (x=left, y=top)
const DESK_POS: Record<string, { x: number; y: number }> = {
  writer:     { x: 11,  y: 18 },
  analyzer:   { x: 30,  y: 18 },
  optimizer:  { x: 11,  y: 57 },
  enhancer:   { x: 60,  y: 18 },
  uploader:   { x: 79,  y: 18 },
  translator: { x: 60,  y: 57 },
  scheduler:  { x: 44,  y: 81 },
}
const MGR_POS = { x: 44, y: 81 }

// Akiya agents cycle through predefined thoughts (separate project, no live SSE)
const AKIYA_CYCLES: Record<string, { thought: string; status: string; detail?: string }[]> = {
  enhancer: [
    { thought: '新着物件の承認を監視中...', status: 'idle', detail: 'Supabase リアルタイム接続' },
    { thought: 'Groq API 接続済み・準備完了', status: 'idle', detail: 'llama-3.3-70b-versatile' },
    { thought: '🤔 次の物件はどこから来るんだろう', status: 'thinking' },
    { thought: 'AIタグ生成エンジン準備完了', status: 'idle', detail: '5カテゴリ対応' },
  ],
  uploader: [
    { thought: 'CSV一括登録の待機中...', status: 'idle', detail: '最大500件/回' },
    { thought: '🤔 エージェントからCSVが届かないな', status: 'thinking' },
    { thought: '都道府県名の正規化モジュール待機', status: 'idle' },
    { thought: 'バルクインサート最適化済み', status: 'idle', detail: 'バッチサイズ: 50' },
  ],
  translator: [
    { thought: '英語翻訳エンジン待機中...', status: 'idle', detail: 'Groq 高精度モード' },
    { thought: '🌏 次の翻訳リクエストを待っています', status: 'thinking' },
    { thought: 'USD換算レート確認済み', status: 'idle', detail: '1 USD = 150 JPY' },
    { thought: 'SEO英訳テンプレート読込済み', status: 'idle' },
  ],
}

const STATUS_CFG: Record<string, { label: string; dot: string; pulse: boolean }> = {
  idle:     { label: '待機中',   dot: '#52525b', pulse: false },
  thinking: { label: '考え中',   dot: '#f59e0b', pulse: true  },
  working:  { label: '作業中',   dot: '#818cf8', pulse: true  },
  success:  { label: '完了',     dot: '#22c55e', pulse: false },
  error:    { label: 'エラー',   dot: '#ef4444', pulse: false },
  stuck:    { label: '詰まり中', dot: '#f97316', pulse: true  },
}

// ─────────────────────────────── SVG Components ──────────────────────────────

function PersonSVG({ color, status, size = 28 }: { color: string; status: string; size?: number }) {
  const isWorking = status === 'working' || status === 'thinking'
  const isSuccess = status === 'success'
  const isError = status === 'error'
  const scale = size / 28

  return (
    <svg
      width={28 * scale} height={42 * scale}
      viewBox="0 0 28 42" fill="none"
      style={{ overflow: 'visible' }}
    >
      {/* shadow */}
      <ellipse cx="14" cy="40" rx="8" ry="2" fill="#000" opacity={0.12} />
      {/* body */}
      <rect x="8" y="24" width="12" height="13" rx="5" fill={color} opacity={0.92} />
      {/* left arm */}
      <rect
        x={isWorking ? '2' : '4'} y={isWorking ? '22' : '26'}
        width="6" height="4" rx="2" fill={color}
        style={{ transition: 'all 0.5s ease' }}
      />
      {/* right arm */}
      <rect
        x={isWorking ? '20' : '18'} y={isWorking ? '22' : '26'}
        width="6" height="4" rx="2" fill={color}
        style={{ transition: 'all 0.5s ease' }}
      />
      {/* neck */}
      <rect x="11" y="20" width="6" height="5" rx="2" fill={color} opacity={0.7} />
      {/* head */}
      <circle cx="14" cy="13" r="10" fill={color} />
      {/* eyes */}
      <circle cx="10" cy="11" r="1.8" fill="white" opacity={0.9} />
      <circle cx="18" cy="11" r="1.8" fill="white" opacity={0.9} />
      {/* pupils — shift when working */}
      <circle cx={isWorking ? 11 : 10} cy="11" r="0.9" fill="#111" />
      <circle cx={isWorking ? 19 : 18} cy="11" r="0.9" fill="#111" />
      {/* mouth */}
      {isSuccess
        ? <path d="M10 17 Q14 21 18 17" stroke="white" strokeWidth="1.3" strokeLinecap="round" fill="none" opacity="0.8" />
        : isError
        ? <path d="M10 19 Q14 16 18 19" stroke="white" strokeWidth="1.3" strokeLinecap="round" fill="none" opacity="0.6" />
        : <rect x="10" y="17" width="8" height="1.2" rx="0.6" fill="white" opacity="0.4" />
      }
    </svg>
  )
}

function MonitorSVG({ color, status }: { color: string; status: string }) {
  const isActive = status === 'working' || status === 'thinking'
  return (
    <svg width="56" height="40" viewBox="0 0 56 40" fill="none">
      {/* screen bezel */}
      <rect x="1" y="1" width="54" height="32" rx="3" fill="#0d0d14" stroke={`${color}40`} strokeWidth="1.5" />
      {/* screen content */}
      {isActive ? (
        <>
          {[6, 12, 18, 24].map((y, i) => (
            <rect key={i} x="5" y={y} width={[38, 48, 30, 42][i]} height="2" rx="1"
              fill={color} opacity={0.45}
              style={{ animation: `type-anim 1.6s ${i * 0.22}s ease-in-out infinite` }}
            />
          ))}
        </>
      ) : (
        <text x="28" y="18" textAnchor="middle" fontSize="7" fill={`${color}30`} fontFamily="monospace">idle</text>
      )}
      {/* stand */}
      <rect x="24" y="33" width="8" height="4" rx="1" fill="#1e1e28" />
      <rect x="18" y="37" width="20" height="2.5" rx="1.25" fill="#1e1e28" />
    </svg>
  )
}

function DocumentSVG({ color }: { color: string }) {
  return (
    <svg width="16" height="20" viewBox="0 0 16 20" fill="none">
      <rect x="1" y="1" width="14" height="18" rx="2" fill="white" stroke="#d4d4d4" strokeWidth="0.5" />
      <path d="M3 13.5 L12 7" stroke={color} strokeWidth="0.8" strokeLinecap="round" opacity="0.5" />
      {[5, 8, 11, 14].map((y) => (
        <rect key={y} x="3" y={y} width={y < 13 ? 10 : 7} height="1" rx="0.5" fill="#9ca3af" />
      ))}
    </svg>
  )
}

// ─────────────────────────────── Thought Bubble ──────────────────────────────

function ThoughtBubble({ thought, detail, status, color, flash, isManager = false }: {
  thought: string; detail?: string; status: string; color: string; flash: boolean; isManager?: boolean
}) {
  const cfg = STATUS_CFG[status] ?? STATUS_CFG.idle
  return (
    <div style={{ animation: flash ? 'bubble-pop 0.38s cubic-bezier(0.34,1.56,0.64,1)' : 'none' }}>
      <div
        className="rounded-2xl rounded-bl-none px-3 py-2"
        style={{
          background: isManager ? '#14141e' : '#14141e',
          border: `1.5px solid ${color}${isManager ? '35' : '45'}`,
          boxShadow: `0 4px 18px ${color}14, inset 0 1px 0 ${color}18`,
          minWidth: isManager ? '180px' : '130px',
          maxWidth: isManager ? '220px' : '170px',
        }}
      >
        <div className="flex items-center gap-1.5 mb-1">
          <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{
            background: cfg.dot,
            boxShadow: cfg.pulse ? `0 0 5px ${cfg.dot}` : 'none',
            animation: cfg.pulse ? 'dot-pulse 1.4s ease-in-out infinite' : 'none',
          }} />
          <span className="text-[8px] font-bold uppercase tracking-wider" style={{ color: cfg.dot }}>
            {cfg.label}
          </span>
        </div>
        <p className="text-[10px] text-[#d4d4d8] leading-snug font-medium">{thought}</p>
        {detail && <p className="text-[8px] text-[#52525b] mt-0.5 leading-tight">{detail}</p>}
      </div>
      {/* tail */}
      <div style={{
        width: 0, height: 0,
        marginLeft: '12px',
        borderLeft: '6px solid transparent',
        borderRight: '6px solid transparent',
        borderTop: `8px solid ${color}45`,
      }} />
      <div style={{
        width: 0, height: 0,
        marginLeft: '14px',
        marginTop: '-6px',
        borderLeft: '5px solid transparent',
        borderRight: '5px solid transparent',
        borderTop: '7px solid #14141e',
      }} />
    </div>
  )
}

// ─────────────────────────────── Desk Station ────────────────────────────────

function DeskStation({ agentKey, thought, flash }: {
  agentKey: string; thought: Thought | null; flash: boolean
}) {
  const agent = AGENTS[agentKey]
  const pos = DESK_POS[agentKey]
  const status = thought?.status ?? 'idle'
  const isMgr = agent.dept === 'mgr'

  return (
    <div className="absolute flex flex-col items-center" style={{
      left: `${pos.x}%`, top: `${pos.y}%`,
      transform: 'translateX(-50%)',
      zIndex: 5,
    }}>
      {/* Thought bubble */}
      {thought && (
        <div className="mb-1.5">
          <ThoughtBubble
            thought={thought.thought}
            detail={thought.detail}
            status={status}
            color={agent.color}
            flash={flash}
            isManager={isMgr}
          />
        </div>
      )}

      {/* Person */}
      <PersonSVG color={agent.color} status={status} size={isMgr ? 34 : 26} />

      {/* Monitor */}
      <div className="mt-0.5">
        {isMgr ? (
          // Manager has wider monitor
          <svg width="80" height="44" viewBox="0 0 80 44" fill="none">
            <rect x="1" y="1" width="78" height="34" rx="3" fill="#0d0d14" stroke={`${agent.color}30`} strokeWidth="1.5" />
            <text x="40" y="20" textAnchor="middle" fontSize="7" fill={`${agent.color}50`} fontFamily="monospace">DIRECTOR</text>
            <rect x="32" y="35" width="16" height="4" rx="1" fill="#1e1e28" />
            <rect x="22" y="39" width="36" height="3" rx="1.5" fill="#1e1e28" />
          </svg>
        ) : (
          <MonitorSVG color={agent.color} status={status} />
        )}
      </div>

      {/* Desk surface */}
      <div className="rounded-sm" style={{
        width: isMgr ? '96px' : '64px',
        height: '8px',
        background: '#1a1a24',
        borderTop: `1.5px solid ${agent.color}22`,
        marginTop: '2px',
      }} />

      {/* Small items: keyboard suggestion line */}
      <div style={{ width: isMgr ? 80 : 52, height: 3, background: '#27272e', borderRadius: 2, marginTop: 2 }} />

      {/* Name label */}
      <div className="text-center mt-1.5">
        <p className="text-[9px] font-bold" style={{ color: agent.color }}>{agent.name}</p>
        <p className="text-[7px] text-[#3f3f46]">{agent.role}</p>
        {agent.dept === 'akiya' && (
          <span className="text-[6px] text-[#fbbf24]/50 mt-0.5 block">● オンコール</span>
        )}
        {agent.dept === 'seo' && (
          <span className="text-[6px] text-[#818cf8]/50 mt-0.5 block">● 常駐</span>
        )}
        {agent.dept === 'mgr' && (
          <span className="text-[6px] text-[#22c55e]/50 mt-0.5 block">● 部長</span>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────── Walking Figure ──────────────────────────────

function WalkingAgent({ pos, color, hasDoc }: {
  pos: { x: number; y: number }; color: string; hasDoc: boolean
}) {
  return (
    <div className="absolute pointer-events-none" style={{
      left: `${pos.x}%`,
      top: `${pos.y}%`,
      transform: 'translate(-50%, -100%)',
      transition: 'left 1.5s cubic-bezier(0.4, 0, 0.2, 1), top 1.5s cubic-bezier(0.4, 0, 0.2, 1)',
      zIndex: 50,
      filter: `drop-shadow(0 0 8px ${color}90)`,
    }}>
      <div style={{ position: 'relative', display: 'inline-block' }}>
        {/* Walking SVG figure */}
        <svg width="22" height="36" viewBox="0 0 22 36" fill="none"
          style={{ animation: 'walk-bob 0.3s ease-in-out infinite alternate' }}>
          {/* head */}
          <circle cx="11" cy="6" r="6" fill={color} />
          {/* body */}
          <rect x="7" y="13" width="8" height="11" rx="3" fill={color} />
          {/* left arm */}
          <rect x="1" y="14" width="7" height="4" rx="2" fill={color}
            style={{ animation: 'walk-arm-l 0.3s ease-in-out infinite alternate', transformOrigin: '4px 16px' }} />
          {/* right arm */}
          <rect x="14" y="14" width="7" height="4" rx="2" fill={color}
            style={{ animation: 'walk-arm-r 0.3s ease-in-out infinite alternate', transformOrigin: '18px 16px' }} />
          {/* left leg */}
          <rect x="6" y="24" width="4" height="10" rx="2" fill={color}
            style={{ animation: 'walk-leg-l 0.3s ease-in-out infinite alternate', transformOrigin: '8px 24px' }} />
          {/* right leg */}
          <rect x="12" y="24" width="4" height="10" rx="2" fill={color}
            style={{ animation: 'walk-leg-r 0.3s ease-in-out infinite alternate', transformOrigin: '14px 24px' }} />
        </svg>

        {/* Document carried */}
        {hasDoc && (
          <div style={{
            position: 'absolute',
            top: '-4px',
            right: '-14px',
            animation: 'doc-carry 0.3s ease-in-out infinite alternate',
          }}>
            <DocumentSVG color={color} />
          </div>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────── Submit Burst ────────────────────────────────

function SubmitBurst({ pos, color }: { pos: { x: number; y: number }; color: string }) {
  return (
    <div className="absolute pointer-events-none" style={{
      left: `${pos.x}%`,
      top: `${pos.y - 4}%`,
      transform: 'translate(-50%, -100%)',
      zIndex: 60,
      animation: 'submit-float 1s ease-out forwards',
    }}>
      <div className="flex items-center gap-1 text-[11px] font-bold" style={{ color }}>
        <span>✓</span>
        <span>提出完了!</span>
      </div>
    </div>
  )
}

// ─────────────────────────────── Activity Feed ───────────────────────────────

function ActivityFeed({ logs }: { logs: Thought[] }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [logs])

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-[#1e1e28] flex items-center justify-between flex-shrink-0">
        <span className="text-[9px] font-bold tracking-widest uppercase text-[#3f3f46]">Activity Log</span>
        <span className="text-[8px] font-mono text-[#27272e]">{logs.length} events</span>
      </div>
      <div ref={ref} className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
        {logs.length === 0 && (
          <p className="text-[10px] text-[#27272e] text-center mt-8">接続待機中...</p>
        )}
        {logs.map((log, i) => {
          const agent = AGENTS[log.agent]
          const cfg = STATUS_CFG[log.status] ?? STATUS_CFG.idle
          const isNew = i === logs.length - 1
          return (
            <div
              key={i}
              className="flex gap-1.5 px-2 py-1.5 rounded-lg hover:bg-[#111118] transition-colors"
              style={{ animation: isNew ? 'feed-in 0.2s ease' : 'none' }}
            >
              <div className="w-1 h-1 rounded-full mt-1.5 flex-shrink-0"
                style={{ background: agent?.color ?? '#52525b' }} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1 mb-0.5 flex-wrap">
                  <span className="text-[8px] font-bold" style={{ color: agent?.color ?? '#71717a' }}>
                    {agent?.name ?? log.agent}
                  </span>
                  <span className="text-[7px] px-1 rounded"
                    style={{ background: `${cfg.dot}18`, color: cfg.dot }}>
                    {cfg.label}
                  </span>
                  <span className="text-[7px] text-[#27272e] ml-auto font-mono">
                    {new Date(log.ts).toLocaleTimeString('ja-JP', {
                      hour: '2-digit', minute: '2-digit', second: '2-digit',
                    })}
                  </span>
                </div>
                <p className="text-[9px] text-[#71717a] leading-snug truncate">{log.thought}</p>
                {log.detail && (
                  <p className="text-[8px] text-[#3f3f46] truncate">{log.detail}</p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─────────────────────────────── Clock ───────────────────────────────────────

function Clock() {
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return (
    <span className="font-mono text-[9px] text-[#3f3f46]">
      {time.toLocaleTimeString('ja-JP')}
    </span>
  )
}

// ─────────────────────────────── Office Decorations ──────────────────────────

function Plant({ style }: { style?: React.CSSProperties }) {
  return (
    <svg width="20" height="32" viewBox="0 0 20 32" fill="none" style={style}>
      <rect x="7" y="26" width="6" height="6" rx="1.5" fill="#1a1a24" />
      <ellipse cx="10" cy="17" rx="8" ry="11" fill="#14532d" opacity="0.75" />
      <ellipse cx="6" cy="14" rx="5" ry="7" fill="#166534" opacity="0.65" />
      <ellipse cx="14" cy="14" rx="5" ry="7" fill="#166534" opacity="0.65" />
      <rect x="9" y="14" width="2" height="13" rx="1" fill="#15803d" opacity="0.5" />
    </svg>
  )
}

function CoffeeMachine({ style }: { style?: React.CSSProperties }) {
  return (
    <svg width="22" height="30" viewBox="0 0 22 30" fill="none" style={style}>
      <rect x="3" y="7" width="16" height="21" rx="3" fill="#1e1e2e" />
      <rect x="6" y="3" width="10" height="6" rx="2" fill="#27273a" />
      <circle cx="11" cy="18" r="4" fill="#0d0d18" />
      <circle cx="11" cy="18" r="2.5" fill="#6366f1" opacity="0.3" />
      <circle cx="11" cy="18" r="1" fill="#818cf8" opacity="0.5" />
      <rect x="14" y="10" width="2" height="3" rx="1" fill="#818cf8" opacity="0.4" />
    </svg>
  )
}

function Whiteboard({ style }: { style?: React.CSSProperties }) {
  return (
    <svg width="44" height="32" viewBox="0 0 44 32" fill="none" style={style}>
      <rect x="1" y="1" width="42" height="28" rx="2" fill="#13131f" stroke="#27272e" strokeWidth="1" />
      <rect x="1" y="27" width="42" height="4" rx="1" fill="#1e1e2e" />
      <text x="22" y="10" textAnchor="middle" fontSize="5" fill="#818cf8" opacity="0.6" fontFamily="monospace">ARTICLES</text>
      <rect x="6" y="13" width="32" height="1" rx="0.5" fill="#818cf8" opacity="0.25" />
      <rect x="6" y="17" width="20" height="1" rx="0.5" fill="#34d399" opacity="0.25" />
      <rect x="6" y="21" width="26" height="1" rx="0.5" fill="#a78bfa" opacity="0.25" />
    </svg>
  )
}

// ─────────────────────────────── Main Page ───────────────────────────────────

export default function OfficePage() {
  const [thoughts, setThoughts] = useState<Record<string, Thought>>({})
  const [akiyaThoughts, setAkiyaThoughts] = useState<Record<string, Thought>>({})
  const [activityLog, setActivityLog] = useState<Thought[]>([])
  const [flashMap, setFlashMap] = useState<Record<string, boolean>>({})
  const [connected, setConnected] = useState(false)
  const [walker, setWalker] = useState<Walker | null>(null)
  const [showSubmit, setShowSubmit] = useState(false)
  const walkerLock = useRef(false)
  const akiyaIdxRef = useRef<Record<string, number>>({ enhancer: 0, uploader: 0, translator: 0 })

  // ── Akiya simulated thought cycling ──────────────────────────────────────
  useEffect(() => {
    const init: Record<string, Thought> = {}
    for (const key of Object.keys(AKIYA_CYCLES)) {
      init[key] = { agent: key, ...AKIYA_CYCLES[key][0], ts: new Date().toISOString() }
    }
    setAkiyaThoughts(init)

    const intervals = Object.keys(AKIYA_CYCLES).map((key, idx) =>
      setInterval(() => {
        akiyaIdxRef.current[key] = (akiyaIdxRef.current[key] + 1) % AKIYA_CYCLES[key].length
        const next = AKIYA_CYCLES[key][akiyaIdxRef.current[key]]
        const t: Thought = { agent: key, ...next, ts: new Date().toISOString() }
        setAkiyaThoughts(prev => ({ ...prev, [key]: t }))
        setFlashMap(prev => ({ ...prev, [key]: true }))
        setTimeout(() => setFlashMap(prev => ({ ...prev, [key]: false })), 400)
      }, 8000 + idx * 2900)
    )
    return () => intervals.forEach(clearInterval)
  }, [])

  // ── Live SSE for SEO agents ───────────────────────────────────────────────
  useEffect(() => {
    const es = new EventSource('/api/thoughts/stream')
    es.onopen = () => setConnected(true)
    es.onerror = () => setConnected(false)
    es.onmessage = (e) => {
      const data: Thought = JSON.parse(e.data)
      if (data.ping) return
      setThoughts(prev => ({ ...prev, [data.agent]: data }))
      setActivityLog(prev => [...prev, data].slice(-120))
      setFlashMap(prev => ({ ...prev, [data.agent]: true }))
      setTimeout(() => setFlashMap(prev => ({ ...prev, [data.agent]: false })), 400)
      // Trigger walk on success
      if (data.status === 'success' && data.agent !== 'scheduler' && DESK_POS[data.agent]) {
        triggerWalk(data.agent, AGENTS[data.agent]?.color ?? '#818cf8')
      }
    }
    return () => es.close()
  }, [])

  // ── Walk animation logic ──────────────────────────────────────────────────
  function triggerWalk(agentKey: string, color: string) {
    if (walkerLock.current) return
    walkerLock.current = true

    const startPos = DESK_POS[agentKey]
    setWalker({ agentKey, color, pos: startPos, hasDoc: true, phase: 'to' })

    // Start walking to manager (next 2 frames to trigger CSS transition)
    requestAnimationFrame(() => requestAnimationFrame(() => {
      setWalker(prev => prev ? { ...prev, pos: MGR_POS } : null)
    }))

    // Arrive at manager desk — drop document, show burst
    setTimeout(() => {
      setShowSubmit(true)
      setWalker(prev => prev ? { ...prev, hasDoc: false, phase: 'submit' } : null)
    }, 1600)

    // Walk back
    setTimeout(() => {
      setShowSubmit(false)
      setWalker(prev => prev ? { ...prev, pos: startPos, phase: 'back' } : null)
    }, 2500)

    // Done
    setTimeout(() => {
      setWalker(null)
      walkerLock.current = false
    }, 4200)
  }

  const allThoughts = { ...akiyaThoughts, ...thoughts }
  const seoAgents = ['writer', 'analyzer', 'optimizer']
  const akiyaAgents = ['enhancer', 'uploader', 'translator']

  return (
    <div className="h-screen flex flex-col bg-[#09090b] overflow-hidden">

      {/* CSS Animations */}
      <style>{`
        @keyframes bubble-pop {
          0%   { transform: scale(0.75) translateY(6px); opacity: 0.5; }
          65%  { transform: scale(1.06); opacity: 1; }
          100% { transform: scale(1) translateY(0); opacity: 1; }
        }
        @keyframes dot-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.3; transform: scale(0.6); }
        }
        @keyframes type-anim {
          0%, 100% { opacity: 0.12; transform: scaleX(0.4); transform-origin: left; }
          50%      { opacity: 0.55; transform: scaleX(1); }
        }
        @keyframes walk-bob {
          from { transform: translateY(0); }
          to   { transform: translateY(-3px); }
        }
        @keyframes walk-leg-l {
          from { transform: rotate(-22deg); }
          to   { transform: rotate(22deg); }
        }
        @keyframes walk-leg-r {
          from { transform: rotate(22deg); }
          to   { transform: rotate(-22deg); }
        }
        @keyframes walk-arm-l {
          from { transform: rotate(-18deg); }
          to   { transform: rotate(18deg); }
        }
        @keyframes walk-arm-r {
          from { transform: rotate(18deg); }
          to   { transform: rotate(-18deg); }
        }
        @keyframes doc-carry {
          from { transform: rotate(-5deg) translateY(0); }
          to   { transform: rotate(5deg) translateY(-2px); }
        }
        @keyframes submit-float {
          0%   { opacity: 0; transform: translate(-50%, 0) scale(0.8); }
          25%  { opacity: 1; transform: translate(-50%, -14px) scale(1.1); }
          70%  { opacity: 1; transform: translate(-50%, -22px) scale(1); }
          100% { opacity: 0; transform: translate(-50%, -36px) scale(0.9); }
        }
        @keyframes feed-in {
          from { opacity: 0; transform: translateX(-6px); }
          to   { opacity: 1; transform: translateX(0); }
        }
        @keyframes ambient-pulse {
          0%, 100% { opacity: 0.25; }
          50%       { opacity: 0.45; }
        }
        @keyframes window-flicker {
          0%, 96%, 100% { opacity: 1; }
          97%           { opacity: 0.85; }
          98%           { opacity: 1; }
          99%           { opacity: 0.9; }
        }
      `}</style>

      {/* ── Header ───────────────────────────────────────────────────────────── */}
      <header className="border-b border-[#1e1e28] bg-[#0d0d12] px-5 h-12 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <a href="/admin" className="text-[#3f3f46] hover:text-[#71717a] text-xs transition-colors">
            ← ダッシュボード
          </a>
          <span className="text-[#1e1e26]">/</span>
          <span className="text-sm font-semibold">🏢 オフィス ライブビュー</span>
        </div>
        <div className="flex items-center gap-4">
          {/* Department legend */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-sm" style={{ background: '#818cf8' }} />
              <span className="text-[9px] text-[#52525b]">SEO部門 (常駐)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-sm" style={{ background: '#fbbf24' }} />
              <span className="text-[9px] text-[#52525b]">空き家部門 (オンコール)</span>
            </div>
          </div>
          {/* Connection */}
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full" style={{
              background: connected ? '#22c55e' : '#ef4444',
              boxShadow: connected ? '0 0 5px #22c55e80' : 'none',
              animation: connected ? 'dot-pulse 2s infinite' : 'none',
            }} />
            <span className="text-[9px] text-[#3f3f46]">{connected ? 'LIVE' : 'OFFLINE'}</span>
          </div>
          {/* Clock */}
          <Clock />
        </div>
      </header>

      <div className="flex flex-1 min-h-0">

        {/* ── Office Floor ─────────────────────────────────────────────────── */}
        <div className="flex-1 relative overflow-hidden">

          {/* Floor tile pattern */}
          <div className="absolute inset-0 opacity-[0.025]" style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)
            `,
            backgroundSize: '44px 44px',
          }} />

          {/* Ceiling ambient glow */}
          <div className="absolute inset-0 pointer-events-none" style={{
            background: 'radial-gradient(ellipse 80% 30% at 50% 0%, #18182a25, transparent 65%)',
            animation: 'ambient-pulse 8s ease-in-out infinite',
          }} />

          {/* Window light (top-left wall) */}
          <div className="absolute" style={{
            left: '-10px', top: '-10px',
            width: '180px', height: '160px',
            background: 'radial-gradient(ellipse at 0% 0%, #fbbf2408, transparent 70%)',
            animation: 'window-flicker 12s ease-in-out infinite',
          }} />

          {/* ── SEO Department Room ──────────────────────────────────────── */}
          <div className="absolute" style={{
            left: '1.5%', top: '3%',
            width: '46.5%', height: '72%',
            border: '1px solid #818cf818',
            borderRadius: '12px',
            background: 'linear-gradient(145deg, #818cf806 0%, transparent 55%)',
          }} />

          {/* SEO department sign */}
          <div className="absolute" style={{ left: '4%', top: '4.5%' }}>
            <div className="flex items-center gap-1.5">
              <div className="h-px w-4" style={{ background: '#818cf8' }} />
              <p className="text-[8px] font-bold tracking-[0.2em] uppercase" style={{ color: '#818cf8' }}>
                SEO部門
              </p>
            </div>
            <p className="text-[7px] text-[#3f3f46] mt-0.5">OpenClaw Real Estate · 常駐AI</p>
          </div>

          {/* ── Akiya Department Room ────────────────────────────────────── */}
          <div className="absolute" style={{
            left: '52%', top: '3%',
            width: '46.5%', height: '72%',
            border: '1px solid #fbbf2418',
            borderRadius: '12px',
            background: 'linear-gradient(145deg, #fbbf2406 0%, transparent 55%)',
          }} />

          {/* Akiya department sign */}
          <div className="absolute" style={{ left: '55%', top: '4.5%' }}>
            <div className="flex items-center gap-1.5">
              <div className="h-px w-4" style={{ background: '#fbbf24' }} />
              <p className="text-[8px] font-bold tracking-[0.2em] uppercase" style={{ color: '#fbbf24' }}>
                空き家部門
              </p>
            </div>
            <p className="text-[7px] text-[#3f3f46] mt-0.5">Akiya Japan Portal · オンコールAI</p>
          </div>

          {/* ── Glass partition between departments ──────────────────────── */}
          <div className="absolute" style={{
            left: '49.2%', top: '5%', width: '1.6%', height: '65%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <div style={{
              width: '1px', height: '100%',
              background: 'linear-gradient(to bottom, transparent 0%, #2a2a3a 15%, #2a2a3a 85%, transparent 100%)',
            }} />
          </div>

          {/* ── Manager's Office ─────────────────────────────────────────── */}
          <div className="absolute" style={{
            left: '20%', top: '77%',
            width: '60%', height: '20%',
            border: '1px solid #cbd5e120',
            borderRadius: '10px',
            background: 'linear-gradient(180deg, #cbd5e106 0%, transparent 100%)',
          }} />
          <div className="absolute" style={{ left: '33%', top: '78%' }}>
            <p className="text-[7px] tracking-[0.25em] text-[#3f3f46] uppercase">— 部長室 · Manager's Office —</p>
          </div>

          {/* ── Corridor label ───────────────────────────────────────────── */}
          <div className="absolute" style={{ left: '42%', top: '74.5%' }}>
            <p className="text-[7px] text-[#27272e] tracking-widest">廊下</p>
          </div>

          {/* ── Agent Desk Stations ──────────────────────────────────────── */}
          {seoAgents.map(key => (
            <DeskStation key={key} agentKey={key}
              thought={allThoughts[key] ?? null} flash={flashMap[key] ?? false} />
          ))}
          {akiyaAgents.map(key => (
            <DeskStation key={key} agentKey={key}
              thought={allThoughts[key] ?? null} flash={flashMap[key] ?? false} />
          ))}
          <DeskStation agentKey="scheduler"
            thought={allThoughts['scheduler'] ?? null} flash={flashMap['scheduler'] ?? false} />

          {/* ── Walking Agent ────────────────────────────────────────────── */}
          {walker && (
            <WalkingAgent pos={walker.pos} color={walker.color} hasDoc={walker.hasDoc} />
          )}

          {/* ── Submit Burst ─────────────────────────────────────────────── */}
          {showSubmit && <SubmitBurst pos={MGR_POS} color="#22c55e" />}

          {/* ── Office Decorations ───────────────────────────────────────── */}
          {/* Plants */}
          <Plant style={{ position: 'absolute', bottom: '4%', left: '2%', opacity: 0.35 }} />
          <Plant style={{ position: 'absolute', bottom: '4%', left: '48%', opacity: 0.3 }} />
          <Plant style={{ position: 'absolute', top: '5%', right: '2%', opacity: 0.25 }} />

          {/* Coffee machine */}
          <CoffeeMachine style={{ position: 'absolute', bottom: '4%', left: '18%', opacity: 0.3 }} />
          <CoffeeMachine style={{ position: 'absolute', bottom: '4%', right: '5%', opacity: 0.25 }} />

          {/* Whiteboard */}
          <Whiteboard style={{ position: 'absolute', bottom: '5%', left: '33%', opacity: 0.35 }} />
        </div>

        {/* ── Activity Feed Sidebar ─────────────────────────────────────────── */}
        <div className="w-60 flex-shrink-0 border-l border-[#1e1e28] bg-[#0a0a0e] flex flex-col">
          <ActivityFeed logs={activityLog} />
        </div>

      </div>
    </div>
  )
}
