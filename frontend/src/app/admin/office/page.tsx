'use client'

import { useState, useEffect, useRef } from 'react'

// ══════════════════════════════════════════════════════
//  TYPES
// ══════════════════════════════════════════════════════

type Thought = {
  agent: string; thought: string; status: string; detail?: string; ts: string; ping?: boolean
}
type Zone = 'work' | 'idle' | 'bug'
type WalkerState = {
  agentKey: string; color: string
  pos: { x: number; y: number }
  hasDoc: boolean
}

// ══════════════════════════════════════════════════════
//  CONFIG — AGENTS
// ══════════════════════════════════════════════════════

const AGENTS: Record<string, {
  name: string; role: string; color: string; body: string; dept: 'seo' | 'akiya' | 'mgr'
}> = {
  writer:     { name: 'WriterAgent',    role: '記事執筆',     color: '#818cf8', body: '#4f46e5', dept: 'seo'   },
  analyzer:   { name: 'AnalyzerAgent',  role: 'アクセス分析', color: '#c4b5fd', body: '#7c3aed', dept: 'seo'   },
  optimizer:  { name: 'OptimizerAgent', role: '記事最適化',   color: '#34d399', body: '#059669', dept: 'seo'   },
  enhancer:   { name: 'EnhanceAgent',   role: '物件AI強化',   color: '#fcd34d', body: '#d97706', dept: 'akiya' },
  uploader:   { name: 'UploadAgent',    role: 'CSV一括登録',  color: '#fb923c', body: '#ea580c', dept: 'akiya' },
  translator: { name: 'TranslateAgent', role: '英語自動翻訳', color: '#f9a8d4', body: '#be185d', dept: 'akiya' },
  scheduler:  { name: 'Scheduler',      role: '部長',         color: '#fde68a', body: '#b45309', dept: 'mgr'   },
}

// ══════════════════════════════════════════════════════
//  CONFIG — ZONE POSITIONS (% of floor)
//  Work zone: 作業ゾーン  Idle zone: 休憩ゾーン  Bug zone: バグゾーン
// ══════════════════════════════════════════════════════

const AGENT_ZONES: Record<string, Record<Zone, { x: number; y: number }>> = {
  // SEO dept (room: x 1.5–47%, y 5–74%)
  writer:     { work: {x: 9,  y:22}, idle: {x:35, y:26}, bug: {x: 9,  y:60} },
  analyzer:   { work: {x:21,  y:22}, idle: {x:38, y:39}, bug: {x:17,  y:60} },
  optimizer:  { work: {x: 9,  y:43}, idle: {x:35, y:52}, bug: {x:25,  y:60} },
  // Akiya dept (room: x 52–98%, y 5–74%)
  enhancer:   { work: {x:59,  y:22}, idle: {x:83, y:26}, bug: {x:59,  y:60} },
  uploader:   { work: {x:71,  y:22}, idle: {x:85, y:39}, bug: {x:67,  y:60} },
  translator: { work: {x:59,  y:43}, idle: {x:83, y:52}, bug: {x:75,  y:60} },
}
const MGR_POS = { x: 44, y: 81 }

function statusToZone(status: string): Zone {
  if (status === 'working' || status === 'thinking') return 'work'
  if (status === 'error' || status === 'stuck') return 'bug'
  return 'idle'
}

// ══════════════════════════════════════════════════════
//  AKIYA SIMULATED THOUGHTS (separate Vercel project)
// ══════════════════════════════════════════════════════

const AKIYA_CYCLES: Record<string, { thought: string; status: string; detail?: string }[]> = {
  enhancer: [
    { thought: '新着物件の承認を監視中...', status: 'idle',     detail: 'Supabase リアルタイム接続' },
    { thought: 'AIタグ生成の準備完了',       status: 'idle',     detail: '5カテゴリ対応' },
    { thought: '次の物件タスクを受信中',       status: 'thinking', detail: 'Groq API 接続確認中...' },
    { thought: 'タグ生成エンジン稼働中',       status: 'working',  detail: 'llama-3.3-70b-versatile' },
    { thought: '✅ AI強化完了',              status: 'idle',     detail: 'タグ + スラッグ生成済み' },
  ],
  uploader: [
    { thought: 'CSV一括登録の待機中',         status: 'idle',     detail: '最大500件/回' },
    { thought: '🤔 CSVファイルを待ってます',  status: 'thinking' },
    { thought: 'スキーマ検証モジュール起動',   status: 'working',  detail: '都道府県名を正規化中...' },
    { thought: 'バルクインサート最適化完了',   status: 'idle',     detail: 'バッチサイズ: 50' },
  ],
  translator: [
    { thought: '英語翻訳エンジン待機中',       status: 'idle',     detail: 'Groq 高精度モード' },
    { thought: '🌏 翻訳リクエストを待ってます', status: 'thinking' },
    { thought: 'USD換算レート確認中',          status: 'working',  detail: '1 USD = 150 JPY' },
    { thought: '✅ 英訳テンプレート完成',      status: 'idle',     detail: 'SEO英訳フォーマット済み' },
  ],
}

const STATUS_CFG: Record<string, { label: string; dot: string; pulse: boolean }> = {
  idle:     { label: '待機',   dot: '#4b5563', pulse: false },
  thinking: { label: '考中',   dot: '#f59e0b', pulse: true  },
  working:  { label: '作業',   dot: '#818cf8', pulse: true  },
  success:  { label: '完了',   dot: '#22c55e', pulse: false },
  error:    { label: 'エラー', dot: '#ef4444', pulse: false },
  stuck:    { label: '停止',   dot: '#f97316', pulse: true  },
}

// ══════════════════════════════════════════════════════
//  PIXEL ART CHARACTER  (16×20 logical px, each px = PX CSS px)
// ══════════════════════════════════════════════════════

const PX = 3  // logical pixel → CSS pixel ratio

function Px({ x, y, c }: { x: number; y: number; c: string }) {
  return <rect x={x * PX} y={y * PX} width={PX} height={PX} fill={c} />
}

function PixelChar({ color, body, status }: { color: string; body: string; status: string }) {
  const w = status === 'working' || status === 'thinking'
  const err = status === 'error' || status === 'stuck'
  const ok = status === 'success'
  const skin = '#f4c78e'
  const hair = '#2a1a08'
  const leg  = '#27272a'

  return (
    <svg width={16 * PX} height={20 * PX} viewBox={`0 0 ${16 * PX} ${20 * PX}`}
      style={{ imageRendering: 'pixelated', display: 'block' }}>
      {/* shadow */}
      <ellipse cx={8 * PX} cy={20 * PX - 1} rx={6 * PX} ry={PX * 0.7} fill="#000" opacity={0.15} />
      {/* hair */}
      {[3,4,5,6,7,8,9,10,11,12].map(x => <Px key={x} x={x} y={0} c={hair} />)}
      {[2,13].map(x => <Px key={x} x={x} y={1} c={hair} />)}
      {/* head */}
      {[2,3,4,5,6,7,8,9,10,11,12,13].map(x => [1,2,3,4,5].map(y =>
        <Px key={`${x}${y}`} x={x} y={y} c={skin} />
      ))}
      {/* eyes */}
      <Px x={4}  y={3} c={err ? '#ef4444' : '#111'} />
      <Px x={11} y={3} c={err ? '#ef4444' : '#111'} />
      {/* glasses (scheduler) */}
      {/* mouth */}
      {ok
        ? [5,6,7,8,9,10].map(x => <Px key={x} x={x} y={5} c="#9a4a2a" />)
        : err
        ? [6,7,8,9].map(x => <Px key={x} x={x} y={5} c="#9a4a2a" />)
        : [6,9].map(x => <Px key={x} x={x} y={5} c="#c8855a" />)
      }
      {/* neck */}
      {[6,7,8,9].map(x => <Px key={x} x={x} y={6} c={skin} />)}
      {/* body / shirt */}
      {[3,4,5,6,7,8,9,10,11,12].map(x => [7,8,9,10,11].map(y =>
        <Px key={`${x}${y}`} x={x} y={y} c={body} />
      ))}
      {/* shirt detail line */}
      {[7,8].map(x => <Px key={x} x={x} y={9} c={color} />)}
      {/* left arm */}
      {[w?0:1, w?0:1].map((_, i) => <Px key={i} x={w?1:2} y={8+i} c={body} />)}
      <Px x={w?2:3} y={7} c={body} />
      {/* right arm */}
      {[0,1].map(i => <Px key={i} x={w?13:12} y={8+i} c={body} />)}
      <Px x={w?12:11} y={7} c={body} />
      {/* legs */}
      {[5,6,7].map(y => [<Px key={`l${y}`} x={5} y={12+y} c={leg} />, <Px key={`r${y}`} x={10} y={12+y} c={leg} />])}
      {[5,6,7].map(y => <Px key={y} x={6} y={12+y} c={leg} />)}
      {[5,6,7].map(y => <Px key={y} x={9} y={12+y} c={leg} />)}
    </svg>
  )
}

// ══════════════════════════════════════════════════════
//  THOUGHT BUBBLE
// ══════════════════════════════════════════════════════

function ThoughtBubble({ thought, detail, status, color, flash, isManager = false }: {
  thought: string; detail?: string; status: string; color: string; flash: boolean; isManager?: boolean
}) {
  const cfg = STATUS_CFG[status] ?? STATUS_CFG.idle
  return (
    <div style={{ animation: flash ? 'pop 0.35s cubic-bezier(0.34,1.56,0.64,1)' : 'none' }}>
      <div style={{
        background: '#101018',
        border: `2px solid ${color}60`,
        borderRadius: 0,  // pixel style: no rounding
        padding: '5px 8px',
        minWidth: isManager ? '190px' : '140px',
        maxWidth: isManager ? '230px' : '180px',
        boxShadow: `3px 3px 0 ${color}30`,
      }}>
        {/* Status row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 3 }}>
          <span style={{
            width: 6, height: 6, borderRadius: 0, display: 'inline-block',
            background: cfg.dot,
            boxShadow: cfg.pulse ? `0 0 4px ${cfg.dot}` : 'none',
            animation: cfg.pulse ? 'blink 1.2s step-start infinite' : 'none',
          }} />
          <span style={{
            fontFamily: 'monospace', fontSize: 8, color: cfg.dot,
            textTransform: 'uppercase', letterSpacing: '0.15em',
          }}>
            {cfg.label}
          </span>
        </div>
        <p style={{
          fontFamily: 'monospace', fontSize: 9.5, color: '#e4e4e7',
          lineHeight: 1.45, margin: 0,
        }}>{thought}</p>
        {detail && (
          <p style={{
            fontFamily: 'monospace', fontSize: 8, color: '#52525b',
            marginTop: 3, lineHeight: 1.3,
          }}>{detail}</p>
        )}
      </div>
      {/* pixel tail */}
      <div style={{ display: 'flex', flexDirection: 'column', paddingLeft: 10 }}>
        {[10, 7, 4].map((w, i) => (
          <div key={i} style={{ width: w, height: 3, background: `${color}60` }} />
        ))}
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════
//  FLOATING AGENT  — moves between zones via CSS transition
// ══════════════════════════════════════════════════════

function FloatingAgent({ agentKey, pos, thought, flash, hidden }: {
  agentKey: string
  pos: { x: number; y: number }
  thought: Thought | null
  flash: boolean
  hidden: boolean
}) {
  const agent = AGENTS[agentKey]
  const status = thought?.status ?? 'idle'

  return (
    <div style={{
      position: 'absolute',
      left: `${pos.x}%`,
      top: `${pos.y}%`,
      transform: 'translate(-50%, -100%)',
      transition: 'left 0.85s cubic-bezier(0.4, 0, 0.2, 1), top 0.85s cubic-bezier(0.4, 0, 0.2, 1)',
      zIndex: 10,
      opacity: hidden ? 0 : 1,
    }}>
      {/* Thought bubble */}
      {thought && (
        <div style={{ marginBottom: 4 }}>
          <ThoughtBubble
            thought={thought.thought}
            detail={thought.detail}
            status={status}
            color={agent.color}
            flash={flash}
            isManager={agent.dept === 'mgr'}
          />
        </div>
      )}
      {/* Character */}
      <div style={{ display: 'flex', justifyContent: 'center', position: 'relative' }}>
        <PixelChar color={agent.color} body={agent.body} status={status} />
        {/* Glow when working */}
        {(status === 'working' || status === 'thinking') && (
          <div style={{
            position: 'absolute', inset: -6,
            background: `radial-gradient(circle, ${agent.color}20, transparent 70%)`,
            borderRadius: 0,
            pointerEvents: 'none',
          }} />
        )}
      </div>
      {/* Name tag */}
      <div style={{
        textAlign: 'center', marginTop: 3,
        fontFamily: 'monospace', fontSize: 7.5,
        color: agent.color, letterSpacing: '0.08em',
      }}>{agent.name}</div>
    </div>
  )
}

// ══════════════════════════════════════════════════════
//  WALKING AGENT  — for manager submission animation
// ══════════════════════════════════════════════════════

function WalkingAgent({ pos, color, body, hasDoc }: {
  pos: { x: number; y: number }; color: string; body: string; hasDoc: boolean
}) {
  return (
    <div style={{
      position: 'absolute',
      left: `${pos.x}%`,
      top: `${pos.y}%`,
      transform: 'translate(-50%, -100%)',
      transition: 'left 1.3s cubic-bezier(0.4, 0, 0.2, 1), top 1.3s cubic-bezier(0.4, 0, 0.2, 1)',
      zIndex: 50,
      filter: `drop-shadow(0 0 8px ${color}a0)`,
    }}>
      <div style={{ position: 'relative', display: 'inline-block' }}>
        {/* walk bob */}
        <div style={{ animation: 'walk-bob 0.25s step-start infinite' }}>
          <PixelChar color={color} body={body} status="working" />
        </div>
        {/* document */}
        {hasDoc && (
          <div style={{
            position: 'absolute', top: -4, right: -14,
            background: '#fff', width: 12, height: 15,
            border: '1px solid #ccc', borderRadius: 0,
            boxShadow: '2px 2px 0 #00000030',
            animation: 'doc-bob 0.25s step-start infinite',
          }}>
            {[3, 6, 9, 12].map(top => (
              <div key={top} style={{ position: 'absolute', top, left: 2, right: 2, height: 1, background: '#aaa' }} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function SubmitBurst({ pos, color }: { pos: { x: number; y: number }; color: string }) {
  return (
    <div style={{
      position: 'absolute',
      left: `${pos.x}%`,
      top: `${pos.y - 5}%`,
      transform: 'translate(-50%, -100%)',
      zIndex: 60,
      animation: 'submit-float 0.9s ease-out forwards',
      fontFamily: 'monospace',
      fontSize: 11,
      fontWeight: 'bold',
      color,
      whiteSpace: 'nowrap',
    }}>
      ★ 提出完了!
    </div>
  )
}

// ══════════════════════════════════════════════════════
//  ZONE OVERLAY AREAS
// ══════════════════════════════════════════════════════

function ZoneOverlays({ dept }: { dept: 'seo' | 'akiya' }) {
  const left = dept === 'seo'
  const bx = left ? 1.5 : 52

  const workColor = left ? '#818cf8' : '#fbbf24'
  const idleColor = '#34d399'
  const bugColor  = '#ef4444'

  const zone = (lx: number, ty: number, w: number, h: number, c: string, label: string) => (
    <div style={{
      position: 'absolute',
      left: `${bx + lx}%`, top: `${ty}%`,
      width: `${w}%`, height: `${h}%`,
      border: `1px solid ${c}20`,
      background: `${c}05`,
      boxSizing: 'border-box',
    }}>
      <div style={{
        position: 'absolute', bottom: 3, left: 4,
        fontFamily: 'monospace', fontSize: 7.5,
        color: `${c}55`, letterSpacing: '0.1em',
        textTransform: 'uppercase',
      }}>{label}</div>
    </div>
  )

  return (
    <>
      {zone(0,  8,  24, 60, workColor, '💻 作業ゾーン')}
      {zone(25, 8,  20, 60, idleColor, '🛋 休憩ゾーン')}
      {zone(0,  57, 18, 11, bugColor,  '🐛 バグゾーン')}
    </>
  )
}

// ══════════════════════════════════════════════════════
//  OFFICE PROPS (furniture, decorations)
// ══════════════════════════════════════════════════════

function DeskPixel({ x, y, color }: { x: number; y: number; color: string }) {
  return (
    <div style={{ position: 'absolute', left: `${x}%`, top: `${y}%` }}>
      <svg width={9 * PX} height={5 * PX} viewBox={`0 0 ${9 * PX} ${5 * PX}`}
        style={{ imageRendering: 'pixelated' }}>
        {/* monitor */}
        {[0,1,2,3,4,5,6,7,8].map(x =>
          [0,1,2].map(y => <Px key={`${x}${y}`} x={x} y={y} c="#111" />)
        )}
        {[2,3,4,5,6].map(x => <Px key={x} x={x} y={1} c={color} />)}
        {/* stand */}
        <Px x={4} y={3} c="#333" />
        {/* desk surface */}
        {[0,1,2,3,4,5,6,7,8].map(x => <Px key={x} x={x} y={4} c="#2a2a3a" />)}
      </svg>
    </div>
  )
}

function SofaPixel({ x, y, color }: { x: number; y: number; color: string }) {
  return (
    <div style={{ position: 'absolute', left: `${x}%`, top: `${y}%`, opacity: 0.55 }}>
      <svg width={10 * PX} height={6 * PX} viewBox={`0 0 ${10 * PX} ${6 * PX}`}
        style={{ imageRendering: 'pixelated' }}>
        {/* back */}
        {[0,1,2,3,4,5,6,7,8,9].map(x => [0,1].map(y =>
          <Px key={`${x}${y}`} x={x} y={y} c={color} />
        ))}
        {/* seat */}
        {[1,2,3,4,5,6,7,8].map(x => [2,3,4].map(y =>
          <Px key={`${x}${y}`} x={x} y={y} c={color + 'cc'} />
        ))}
        {/* legs */}
        {[1,8].map(x => <Px key={x} x={x} y={5} c="#444" />)}
      </svg>
    </div>
  )
}

function PlantPixel({ x, y }: { x: number; y: number }) {
  const g = '#166534'
  const pot = '#7c3d10'
  return (
    <div style={{ position: 'absolute', left: `${x}%`, top: `${y}%`, opacity: 0.6 }}>
      <svg width={6 * PX} height={8 * PX} viewBox={`0 0 ${6 * PX} ${8 * PX}`}
        style={{ imageRendering: 'pixelated' }}>
        {/* leaves */}
        {[2,3].map(x => <Px key={x} x={x} y={0} c={g} />)}
        {[1,2,3,4].map(x => <Px key={x} x={x} y={1} c={g} />)}
        {[0,1,2,3,4,5].map(x => <Px key={x} x={x} y={2} c={g} />)}
        {[1,2,3,4].map(x => <Px key={x} x={x} y={3} c={g} />)}
        <Px x={2} y={4} c={g} />
        {/* pot */}
        {[1,2,3,4].map(x => [5,6,7].map(y => <Px key={`${x}${y}`} x={x} y={y} c={pot} />))}
      </svg>
    </div>
  )
}

function BugSignPixel({ x, y }: { x: number; y: number }) {
  return (
    <div style={{ position: 'absolute', left: `${x}%`, top: `${y}%`, opacity: 0.7 }}>
      <svg width={5 * PX} height={5 * PX} viewBox={`0 0 ${5 * PX} ${5 * PX}`}
        style={{ imageRendering: 'pixelated' }}>
        {/* triangle warning */}
        {[[2,0],[1,1],[2,1],[3,1],[0,2],[1,2],[2,2],[3,2],[4,2],
          [0,3],[1,3],[2,3],[3,3],[4,3]].map(([x,y],i) =>
          <Px key={i} x={x} y={y} c="#ef4444" />
        )}
        <Px x={2} y={1} c="#fbbf24" />
        <Px x={2} y={2} c="#fbbf24" />
        <Px x={2} y={3} c="#fbbf24" />
      </svg>
    </div>
  )
}

// ══════════════════════════════════════════════════════
//  ACTIVITY FEED
// ══════════════════════════════════════════════════════

function ActivityFeed({ logs }: { logs: Thought[] }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [logs])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{
        padding: '10px 14px', borderBottom: '2px solid #1e1e2e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span style={{ fontFamily: 'monospace', fontSize: 9, color: '#3f3f46', letterSpacing: '0.2em' }}>
          ACTIVITY LOG
        </span>
        <span style={{ fontFamily: 'monospace', fontSize: 8, color: '#27272e' }}>{logs.length}</span>
      </div>
      <div ref={ref} style={{ flex: 1, overflowY: 'auto', padding: '6px 8px' }}>
        {logs.length === 0 && (
          <p style={{ fontFamily: 'monospace', fontSize: 9, color: '#27272e', textAlign: 'center', marginTop: 24 }}>
            接続待機中...
          </p>
        )}
        {logs.map((log, i) => {
          const ag = AGENTS[log.agent]
          const cfg = STATUS_CFG[log.status] ?? STATUS_CFG.idle
          const isNew = i === logs.length - 1
          return (
            <div key={i} style={{
              display: 'flex', gap: 6, padding: '5px 6px',
              borderBottom: '1px solid #111118',
              animation: isNew ? 'feed-in 0.2s ease' : 'none',
            }}>
              <div style={{
                width: 3, minWidth: 3, borderRadius: 0,
                background: ag?.color ?? '#52525b', marginTop: 2,
              }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
                  <span style={{ fontFamily: 'monospace', fontSize: 7.5, fontWeight: 'bold', color: ag?.color ?? '#71717a' }}>
                    {ag?.name ?? log.agent}
                  </span>
                  <span style={{
                    fontFamily: 'monospace', fontSize: 7,
                    padding: '0 3px', background: `${cfg.dot}18`, color: cfg.dot,
                  }}>{cfg.label}</span>
                  <span style={{ fontFamily: 'monospace', fontSize: 7, color: '#27272e', marginLeft: 'auto' }}>
                    {new Date(log.ts).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                </div>
                <p style={{ fontFamily: 'monospace', fontSize: 8.5, color: '#71717a', margin: 0, lineHeight: 1.4, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                  {log.thought}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════
//  MAIN PAGE
// ══════════════════════════════════════════════════════

export default function OfficePage() {
  const [thoughts, setThoughts] = useState<Record<string, Thought>>({})
  const [akiyaThoughts, setAkiyaThoughts] = useState<Record<string, Thought>>({})
  const [activityLog, setActivityLog] = useState<Thought[]>([])
  const [flashMap, setFlashMap] = useState<Record<string, boolean>>({})
  const [connected, setConnected] = useState(false)

  // Agent positions — start at idle zone
  const [agentPositions, setAgentPositions] = useState<Record<string, { x: number; y: number }>>(() => {
    const init: Record<string, { x: number; y: number }> = { scheduler: MGR_POS }
    for (const k of Object.keys(AGENT_ZONES)) init[k] = AGENT_ZONES[k].idle
    return init
  })

  // Walker for manager submission
  const [walker, setWalker] = useState<WalkerState | null>(null)
  const [showSubmit, setShowSubmit] = useState(false)
  const [hiddenAgents, setHiddenAgents] = useState<Set<string>>(new Set())
  const walkerLock = useRef(false)

  const [tick, setTick] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setTick(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  // Move agent to zone based on status
  function moveToZone(agentKey: string, status: string) {
    if (!AGENT_ZONES[agentKey]) return
    const zone = statusToZone(status)
    setAgentPositions(prev => ({ ...prev, [agentKey]: AGENT_ZONES[agentKey][zone] }))
  }

  // ── Akiya cycling thoughts ───────────────────────────────────────────────
  const akiyaIdx = useRef<Record<string, number>>({ enhancer: 0, uploader: 0, translator: 0 })
  useEffect(() => {
    const init: Record<string, Thought> = {}
    for (const k of Object.keys(AKIYA_CYCLES)) {
      init[k] = { agent: k, ...AKIYA_CYCLES[k][0], ts: new Date().toISOString() }
      moveToZone(k, AKIYA_CYCLES[k][0].status)
    }
    setAkiyaThoughts(init)

    const intervals = Object.keys(AKIYA_CYCLES).map((k, i) =>
      setInterval(() => {
        akiyaIdx.current[k] = (akiyaIdx.current[k] + 1) % AKIYA_CYCLES[k].length
        const next = AKIYA_CYCLES[k][akiyaIdx.current[k]]
        const t: Thought = { agent: k, ...next, ts: new Date().toISOString() }
        setAkiyaThoughts(prev => ({ ...prev, [k]: t }))
        setFlashMap(prev => ({ ...prev, [k]: true }))
        setTimeout(() => setFlashMap(prev => ({ ...prev, [k]: false })), 400)
        moveToZone(k, next.status)
      }, 9000 + i * 3100)
    )
    return () => intervals.forEach(clearInterval)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Live SSE ─────────────────────────────────────────────────────────────
  useEffect(() => {
    const es = new EventSource('/api/thoughts/stream')
    es.onopen = () => setConnected(true)
    es.onerror = () => setConnected(false)
    es.onmessage = (e) => {
      const data: Thought = JSON.parse(e.data)
      if (data.ping) return
      setThoughts(prev => ({ ...prev, [data.agent]: data }))
      setActivityLog(prev => [...prev, data].slice(-150))
      setFlashMap(prev => ({ ...prev, [data.agent]: true }))
      setTimeout(() => setFlashMap(prev => ({ ...prev, [data.agent]: false })), 400)
      // Move to zone
      moveToZone(data.agent, data.status)
      // Walk to manager on success
      if (data.status === 'success' && data.agent !== 'scheduler' && AGENT_ZONES[data.agent]) {
        triggerWalk(data.agent, AGENTS[data.agent]?.color ?? '#818cf8', AGENTS[data.agent]?.body ?? '#4f46e5')
      }
    }
    return () => es.close()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Manager walk ─────────────────────────────────────────────────────────
  function triggerWalk(agentKey: string, color: string, body: string) {
    if (walkerLock.current) return
    walkerLock.current = true
    const startPos = AGENT_ZONES[agentKey].idle

    // Hide agent's FloatingAgent, show WalkingAgent
    setHiddenAgents(prev => new Set(prev).add(agentKey))
    setWalker({ agentKey, color, pos: startPos, hasDoc: true })

    // Walk to manager
    requestAnimationFrame(() => requestAnimationFrame(() => {
      setWalker(prev => prev ? { ...prev, pos: MGR_POS } : null)
    }))

    // Arrive — drop doc, burst
    setTimeout(() => {
      setShowSubmit(true)
      setWalker(prev => prev ? { ...prev, hasDoc: false } : null)
    }, 1400)

    // Walk back
    setTimeout(() => {
      setShowSubmit(false)
      setWalker(prev => prev ? { ...prev, pos: startPos } : null)
    }, 2300)

    // Done — show agent again at idle
    setTimeout(() => {
      setWalker(null)
      setHiddenAgents(prev => { const s = new Set(prev); s.delete(agentKey); return s })
      walkerLock.current = false
    }, 3800)
  }

  const allThoughts = { ...akiyaThoughts, ...thoughts }
  const seoAgents  = ['writer', 'analyzer', 'optimizer']
  const akiyaAgents = ['enhancer', 'uploader', 'translator']

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#080810', overflow: 'hidden', fontFamily: 'monospace' }}>

      {/* ── Global Keyframes ───────────────────────────────────────────────── */}
      <style>{`
        @keyframes pop {
          0%   { transform: scale(0.7) translateY(8px); opacity: 0.4; }
          65%  { transform: scale(1.08); }
          100% { transform: scale(1) translateY(0); opacity: 1; }
        }
        @keyframes blink {
          0%, 49% { opacity: 1; }
          50%, 100%{ opacity: 0; }
        }
        @keyframes walk-bob {
          0%   { transform: translateY(0); }
          50%  { transform: translateY(-3px); }
          100% { transform: translateY(0); }
        }
        @keyframes doc-bob {
          0%, 100% { transform: rotate(-5deg); }
          50%      { transform: rotate(5deg) translateY(-2px); }
        }
        @keyframes submit-float {
          0%   { opacity: 0; transform: translate(-50%, 0); }
          20%  { opacity: 1; transform: translate(-50%, -16px); }
          75%  { opacity: 1; transform: translate(-50%, -28px); }
          100% { opacity: 0; transform: translate(-50%, -44px); }
        }
        @keyframes feed-in {
          from { opacity: 0; transform: translateX(-4px); }
          to   { opacity: 1; transform: none; }
        }
        @keyframes scanlines {
          0%   { background-position: 0 0; }
          100% { background-position: 0 4px; }
        }
        @keyframes room-flicker {
          0%, 97%, 100% { opacity: 1; }
          98%           { opacity: 0.88; }
          99%           { opacity: 0.96; }
        }
      `}</style>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{
        height: 40, flexShrink: 0,
        background: '#0d0d18',
        borderBottom: '2px solid #1e1e2e',
        display: 'flex', alignItems: 'center',
        padding: '0 16px', gap: 16,
      }}>
        <a href="/admin" style={{ fontFamily: 'monospace', fontSize: 9, color: '#3f3f46', textDecoration: 'none', letterSpacing: '0.1em' }}>
          ◀ DASHBOARD
        </a>
        <span style={{ color: '#1e1e2e' }}>|</span>
        <span style={{ fontFamily: 'monospace', fontSize: 10, color: '#818cf8', letterSpacing: '0.2em' }}>
          ▶ OPENCLAW AI OFFICE — LIVE VIEW
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 14 }}>
          {/* Dept legend */}
          <div style={{ display: 'flex', gap: 10 }}>
            {[
              { color: '#818cf8', label: 'SEO部門 [常駐]' },
              { color: '#fbbf24', label: '空き家部門 [オンコール]' },
              { color: '#fde68a', label: '部長' },
            ].map(({ color, label }) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 5, height: 5, background: color }} />
                <span style={{ fontFamily: 'monospace', fontSize: 8, color: '#52525b' }}>{label}</span>
              </div>
            ))}
          </div>
          {/* Connection */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{
              width: 5, height: 5,
              background: connected ? '#22c55e' : '#ef4444',
              animation: connected ? 'blink 1s step-start infinite' : 'none',
            }} />
            <span style={{ fontFamily: 'monospace', fontSize: 8, color: '#52525b' }}>
              {connected ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>
          {/* Clock */}
          <span style={{ fontFamily: 'monospace', fontSize: 9, color: '#3f3f46' }}>
            {tick.toLocaleTimeString('ja-JP')}
          </span>
        </div>
      </div>

      {/* ── Main ──────────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>

        {/* ── Office Floor ──────────────────────────────────────────────────── */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>

          {/* Pixel floor grid */}
          <div style={{
            position: 'absolute', inset: 0,
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px)
            `,
            backgroundSize: '32px 32px',
          }} />

          {/* Scanline overlay */}
          <div style={{
            position: 'absolute', inset: 0, pointerEvents: 'none',
            backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.06) 4px)',
            zIndex: 100,
          }} />

          {/* ── SEO Department Room ─────────────────────────────────────── */}
          <div style={{
            position: 'absolute', left: '1.5%', top: '3%', width: '46%', height: '72%',
            border: '2px solid #818cf825',
            background: 'linear-gradient(160deg, #818cf808 0%, transparent 55%)',
            animation: 'room-flicker 20s ease-in-out infinite',
          }}>
            {/* Zone overlays inside room */}
            <ZoneOverlays dept="seo" />
          </div>
          {/* Room label */}
          <div style={{ position: 'absolute', left: '4%', top: '4.5%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 12, height: 2, background: '#818cf8' }} />
              <span style={{ fontFamily: 'monospace', fontSize: 8, color: '#818cf8', letterSpacing: '0.2em', textTransform: 'uppercase' }}>SEO部門</span>
            </div>
            <div style={{ fontFamily: 'monospace', fontSize: 7, color: '#3f3f46', marginTop: 2 }}>OpenClaw Real Estate · 常駐AI × 3</div>
          </div>

          {/* ── Akiya Department Room ──────────────────────────────────── */}
          <div style={{
            position: 'absolute', left: '52%', top: '3%', width: '46.5%', height: '72%',
            border: '2px solid #fbbf2420',
            background: 'linear-gradient(160deg, #fbbf2406 0%, transparent 55%)',
          }}>
            <ZoneOverlays dept="akiya" />
          </div>
          <div style={{ position: 'absolute', left: '55%', top: '4.5%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 12, height: 2, background: '#fbbf24' }} />
              <span style={{ fontFamily: 'monospace', fontSize: 8, color: '#fbbf24', letterSpacing: '0.2em', textTransform: 'uppercase' }}>空き家部門</span>
            </div>
            <div style={{ fontFamily: 'monospace', fontSize: 7, color: '#3f3f46', marginTop: 2 }}>Akiya Japan Portal · オンコールAI × 3</div>
          </div>

          {/* ── Glass partition ─────────────────────────────────────────── */}
          <div style={{
            position: 'absolute', left: '49.3%', top: '5%', width: 2, height: '65%',
            background: 'linear-gradient(to bottom, transparent, #2a2a3a 15%, #2a2a3a 85%, transparent)',
          }} />

          {/* ── Manager's Office ────────────────────────────────────────── */}
          <div style={{
            position: 'absolute', left: '22%', top: '77%', width: '56%', height: '20%',
            border: '2px solid #fde68a15',
            background: 'linear-gradient(0deg, #fde68a06 0%, transparent 100%)',
          }} />
          <div style={{ position: 'absolute', left: '35%', top: '78%' }}>
            <span style={{ fontFamily: 'monospace', fontSize: 7.5, color: '#3f3f46', letterSpacing: '0.2em' }}>
              ── 部長室 · DIRECTOR'S OFFICE ──
            </span>
          </div>

          {/* ── Corridor ────────────────────────────────────────────────── */}
          <div style={{ position: 'absolute', left: '42%', top: '74.5%' }}>
            <span style={{ fontFamily: 'monospace', fontSize: 7, color: '#1e1e2e', letterSpacing: '0.1em' }}>廊下</span>
          </div>

          {/* ── Office Furniture ─────────────────────────────────────────── */}
          {/* SEO work zone desks */}
          <DeskPixel x={6}  y={26} color="#818cf8" />
          <DeskPixel x={19} y={26} color="#a78bfa" />
          <DeskPixel x={6}  y={48} color="#34d399" />
          {/* SEO idle zone sofa + plant */}
          <SofaPixel  x={27} y={36} color="#1e3a2a" />
          <PlantPixel x={34} y={24} />
          {/* SEO bug zone warning */}
          <BugSignPixel x={2} y={60} />

          {/* Akiya work zone desks */}
          <DeskPixel x={56} y={26} color="#fbbf24" />
          <DeskPixel x={68} y={26} color="#f97316" />
          <DeskPixel x={56} y={48} color="#f9a8d4" />
          {/* Akiya idle zone sofa + plant */}
          <SofaPixel  x={77} y={36} color="#3a2a10" />
          <PlantPixel x={84} y={24} />
          {/* Akiya bug zone warning */}
          <BugSignPixel x={52} y={60} />

          {/* Manager desk (larger) */}
          <div style={{ position: 'absolute', left: '38%', top: '83%' }}>
            <svg width={16 * PX} height={5 * PX} viewBox={`0 0 ${16 * PX} ${5 * PX}`}
              style={{ imageRendering: 'pixelated' }}>
              {[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15].map(x =>
                [0,1,2].map(y => <Px key={`${x}${y}`} x={x} y={y} c={y === 1 ? '#fde68a30' : '#111'} />)
              )}
              {[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15].map(x =>
                <Px key={x} x={x} y={4} c="#2a2a1a" />
              )}
            </svg>
          </div>

          {/* Ambient plants in corners */}
          <PlantPixel x={0.5} y={2.5} />
          <PlantPixel x={95}  y={2.5} />

          {/* ── Floating Agents ─────────────────────────────────────────── */}
          {[...seoAgents, ...akiyaAgents].map(key => (
            <FloatingAgent
              key={key}
              agentKey={key}
              pos={agentPositions[key] ?? AGENT_ZONES[key].idle}
              thought={allThoughts[key] ?? null}
              flash={flashMap[key] ?? false}
              hidden={hiddenAgents.has(key)}
            />
          ))}
          {/* Scheduler (manager) */}
          <FloatingAgent
            agentKey="scheduler"
            pos={MGR_POS}
            thought={allThoughts['scheduler'] ?? null}
            flash={flashMap['scheduler'] ?? false}
            hidden={false}
          />

          {/* ── Walking Agent (manager submission) ──────────────────────── */}
          {walker && (
            <WalkingAgent
              pos={walker.pos}
              color={walker.color}
              body={AGENTS[walker.agentKey]?.body ?? '#4f46e5'}
              hasDoc={walker.hasDoc}
            />
          )}
          {showSubmit && <SubmitBurst pos={MGR_POS} color="#fde68a" />}

        </div>

        {/* ── Activity Feed ──────────────────────────────────────────────── */}
        <div style={{
          width: 220, flexShrink: 0,
          borderLeft: '2px solid #1e1e2e',
          background: '#0a0a12',
          display: 'flex', flexDirection: 'column',
        }}>
          <ActivityFeed logs={activityLog} />
        </div>

      </div>
    </div>
  )
}
