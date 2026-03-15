'use client'

import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

type Log = {
  id: string
  agent_name: string
  task_type: string
  status: string
  input_summary: string
  output_summary: string
  duration_ms: number
  error_message: string
  created_at: string
}

type AgentStatus = {
  agents: Record<string, { model: string; role: string }>
  last_24h: { success_count: number; error_count: number; running_count: number; total_count: number }
  total_articles: number
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    success: 'bg-[var(--green)]',
    error: 'bg-[var(--red)]',
    running: 'bg-[var(--yellow)]',
  }
  return (
    <span className={`inline-block w-1.5 h-1.5 rounded-full ${colors[status] ?? 'bg-[var(--muted)]'} mr-1.5`} />
  )
}

function Badge({ status }: { status: string }) {
  const cfg: Record<string, string> = {
    success: 'text-[var(--green)] bg-[var(--green)]/10 border-[var(--green)]/20',
    error:   'text-[var(--red)] bg-[var(--red)]/10 border-[var(--red)]/20',
    running: 'text-[var(--yellow)] bg-[var(--yellow)]/10 border-[var(--yellow)]/20',
  }
  return (
    <span className={`inline-flex items-center text-[10px] font-medium px-2 py-0.5 rounded border ${cfg[status] ?? 'text-muted bg-surface2 border-border'}`}>
      <StatusDot status={status} />
      {status}
    </span>
  )
}

// ── Webhook Remote Control Panel ─────────────────────────────────────────────
function WebhookPanel() {
  const [token, setToken] = useState('')
  const [result, setResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)

  const call = async (body: object) => {
    if (!token) { setResult('トークンを入力してください'); return }
    setLoading(true); setResult(null)
    try {
      const res = await fetch('/api/webhook', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      setResult(res.ok ? `✅ ${data.message ?? JSON.stringify(data)}` : `❌ ${data.detail ?? JSON.stringify(data)}`)
    } catch { setResult('❌ 接続エラー') }
    setLoading(false)
  }

  const copy = (key: string, text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(key); setTimeout(() => setCopied(null), 1500)
  }

  const host = typeof window !== 'undefined' ? window.location.origin : 'https://your-domain'
  const curlBase = `curl -X POST ${host}/api/webhook \\\n  -H "Authorization: Bearer <WEBHOOK_SECRET>" \\\n  -H "Content-Type: application/json"`
  const examples = [
    { key: 'gen', label: '記事生成', curl: `${curlBase} \\\n  -d '{"action":"generate_article"}'` },
    { key: 'batch', label: 'バッチ生成', curl: `${curlBase} \\\n  -d '{"action":"generate_batch","count":3}'` },
    { key: 'opt', label: '最適化', curl: `${curlBase} \\\n  -d '{"action":"optimize"}'` },
  ]

  return (
    <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl overflow-hidden mb-5">
      <div className="px-5 py-4 border-b border-[var(--border)] flex items-center justify-between">
        <div>
          <h2 className="text-sm font-medium">外部連携 / Webhook</h2>
          <p className="text-[var(--muted)] text-xs mt-0.5">外部サービスやcurlからエージェントへ指示を送る</p>
        </div>
        <span className="text-[10px] font-mono text-[var(--muted)] bg-[var(--surface2)] border border-[var(--border)] px-2 py-1 rounded">
          POST /api/webhook
        </span>
      </div>
      <div className="p-5">
        <div className="grid md:grid-cols-2 gap-5">
          {/* Left: token input + action buttons */}
          <div className="space-y-3">
            <div>
              <label className="block text-[var(--muted)] text-xs mb-1.5">WEBHOOK_SECRET トークン</label>
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder=".env の WEBHOOK_SECRET を貼り付け"
                className="w-full bg-[var(--surface2)] border border-[var(--border)] hover:border-[var(--border2)] focus:border-[var(--accent)]/50 rounded-lg px-3 py-2 text-sm font-mono outline-none transition-colors"
              />
            </div>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: '記事生成', body: { action: 'generate_article' } },
                { label: 'バッチ×3', body: { action: 'generate_batch', count: 3 } },
                { label: '最適化', body: { action: 'optimize' } },
              ].map(({ label, body }) => (
                <button
                  key={label}
                  onClick={() => call(body)}
                  disabled={loading}
                  className="bg-[var(--accent)]/10 hover:bg-[var(--accent)]/20 border border-[var(--accent)]/30 hover:border-[var(--accent)]/50 text-[var(--accent)] disabled:opacity-40 py-2 rounded-lg text-xs font-medium transition-colors"
                >
                  {loading ? '送信中...' : label}
                </button>
              ))}
            </div>
            {result && (
              <div className="text-xs p-3 bg-[var(--surface2)] border border-[var(--border)] rounded-lg font-mono leading-relaxed">
                {result}
              </div>
            )}
          </div>
          {/* Right: curl examples */}
          <div className="space-y-2">
            <p className="text-[var(--muted)] text-xs mb-2">curl コマンド例</p>
            {examples.map(({ key, label, curl }) => (
              <div key={key} className="relative group">
                <div className="bg-[var(--surface2)] border border-[var(--border)] rounded-lg px-3 py-2 pr-16">
                  <p className="text-[10px] text-[var(--accent)] mb-1 font-medium">{label}</p>
                  <pre className="text-[10px] text-[var(--muted)] font-mono whitespace-pre-wrap break-all leading-relaxed">{curl}</pre>
                </div>
                <button
                  onClick={() => copy(key, curl)}
                  className="absolute right-2 top-2 text-[10px] text-[var(--muted)] hover:text-[var(--text)] bg-[var(--border)] hover:bg-[var(--border2)] px-2 py-1 rounded transition-colors"
                >
                  {copied === key ? '✓' : 'copy'}
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AdminPage() {
  const [status, setStatus] = useState<AgentStatus | null>(null)
  const [logs, setLogs] = useState<Log[]>([])
  const [generating, setGenerating] = useState(false)
  const [message, setMessage] = useState('')
  const [form, setForm] = useState({
    area: '港区',
    prefecture: '東京都',
    property_type: 'マンション',
  })

  const fetchStatus = async () => {
    try {
      const [s, l] = await Promise.all([
        fetch(`/api/agents/status`).then((r) => r.json()),
        fetch(`/api/agents/logs?limit=20`).then((r) => r.json()),
      ])
      setStatus(s)
      setLogs(l)
    } catch {}
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 10000)
    return () => clearInterval(interval)
  }, [])

  const generateArticle = async () => {
    setGenerating(true)
    setMessage('')
    try {
      const res = await fetch('/api/agents/write/article', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      setMessage(`${data.message}`)
      setTimeout(fetchStatus, 3000)
    } catch {
      setMessage('エラーが発生しました')
    } finally {
      setGenerating(false)
    }
  }

  const batchGenerate = async (count: number) => {
    setGenerating(true)
    setMessage('')
    try {
      const res = await fetch('/api/agents/write/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count }),
      })
      const data = await res.json()
      setMessage(data.message)
      setTimeout(fetchStatus, 5000)
    } catch {
      setMessage('エラーが発生しました')
    } finally {
      setGenerating(false)
    }
  }

  const stats = [
    { label: '公開記事数', value: status?.total_articles ?? '—', sub: 'total articles' },
    { label: '24h 成功', value: status?.last_24h?.success_count ?? '—', sub: 'successful runs' },
    { label: '24h エラー', value: status?.last_24h?.error_count ?? '—', sub: 'failed runs' },
    { label: '実行中', value: status?.last_24h?.running_count ?? '—', sub: 'in progress' },
  ]

  return (
    <div className="min-h-screen bg-[var(--bg)]">
      {/* Top bar */}
      <header className="border-b border-[var(--border)] bg-[var(--surface)] sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-5 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Logo mark */}
            <div className="w-7 h-7 rounded-md bg-[var(--accent)]/15 border border-[var(--accent)]/30 flex items-center justify-center">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M2 7L7 2L12 7L7 12L2 7Z" stroke="var(--accent)" strokeWidth="1.5" strokeLinejoin="round"/>
                <circle cx="7" cy="7" r="1.5" fill="var(--accent)"/>
              </svg>
            </div>
            <span className="font-semibold text-sm tracking-tight">OpenClaw</span>
            <span className="text-[var(--border2)] text-sm">/</span>
            <span className="text-[var(--subtle)] text-sm">Agent Dashboard</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 text-[10px] text-[var(--green)] bg-[var(--green)]/10 border border-[var(--green)]/20 px-2.5 py-1 rounded-full">
              <span className="w-1 h-1 rounded-full bg-[var(--green)] animate-pulse" />
              稼働中
            </div>
            <a
              href="/admin/office"
              className="text-xs text-[#8b5cf6] hover:text-[#a78bfa] border border-[#8b5cf6]/30 hover:border-[#8b5cf6]/60 px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5"
            >
              <span>🏢</span> オフィスビュー
            </a>
            <button
              onClick={fetchStatus}
              className="text-xs text-[var(--muted)] hover:text-[var(--text)] border border-[var(--border)] hover:border-[var(--border2)] px-3 py-1.5 rounded-md transition-colors"
            >
              更新
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-5 py-8">

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          {stats.map((s) => (
            <div key={s.label} className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4 hover:border-[var(--border2)] transition-colors">
              <p className="text-[var(--muted)] text-xs mb-2">{s.label}</p>
              <p className="text-3xl font-bold tabular-nums tracking-tight">{s.value}</p>
              <p className="text-[var(--muted)] text-[10px] mt-1">{s.sub}</p>
            </div>
          ))}
        </div>

        <div className="grid md:grid-cols-2 gap-5 mb-8">

          {/* Active agents */}
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[var(--border)] flex items-center justify-between">
              <h2 className="text-sm font-medium">常駐エージェント</h2>
              <span className="text-[10px] text-[var(--muted)] font-mono">{Object.keys(status?.agents ?? {}).length} agents</span>
            </div>
            <div className="p-3 space-y-2">
              {!status ? (
                <div className="px-2 py-6 text-center text-[var(--muted)] text-sm">接続中...</div>
              ) : (
                Object.entries(status.agents).map(([key, agent]) => (
                  <div key={key} className="flex items-center justify-between px-3 py-2.5 rounded-lg bg-[var(--surface2)] hover:bg-[var(--border)]/30 transition-colors">
                    <div>
                      <p className="text-sm font-medium capitalize">{key}</p>
                      <p className="text-[var(--muted)] text-xs">{agent.role}</p>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-1 justify-end mb-0.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-[var(--green)]" />
                        <span className="text-[10px] text-[var(--green)]">active</span>
                      </div>
                      <span className="text-[var(--muted)] text-[10px] font-mono">{agent.model}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Article generator */}
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[var(--border)]">
              <h2 className="text-sm font-medium">記事を今すぐ生成</h2>
              <p className="text-[var(--muted)] text-xs mt-0.5">AIエージェントに記事生成を指示</p>
            </div>
            <div className="p-5 space-y-3">
              {[
                { label: '都道府県', key: 'prefecture' as const },
                { label: 'エリア', key: 'area' as const },
              ].map(({ label, key }) => (
                <div key={key}>
                  <label className="block text-[var(--muted)] text-xs mb-1.5">{label}</label>
                  <input
                    value={form[key]}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    className="w-full bg-[var(--surface2)] border border-[var(--border)] hover:border-[var(--border2)] focus:border-[var(--accent)]/50 rounded-lg px-3 py-2 text-sm outline-none transition-colors"
                  />
                </div>
              ))}
              <div>
                <label className="block text-[var(--muted)] text-xs mb-1.5">物件種別</label>
                <select
                  value={form.property_type}
                  onChange={(e) => setForm({ ...form, property_type: e.target.value })}
                  className="w-full bg-[var(--surface2)] border border-[var(--border)] hover:border-[var(--border2)] rounded-lg px-3 py-2 text-sm outline-none transition-colors"
                >
                  {['マンション', '一戸建て', '土地'].map((t) => (
                    <option key={t}>{t}</option>
                  ))}
                </select>
              </div>

              <div className="flex gap-2 pt-1">
                <button
                  onClick={generateArticle}
                  disabled={generating}
                  className="flex-1 bg-[var(--accent)] hover:bg-[var(--accent-h)] disabled:opacity-40 text-white py-2.5 rounded-lg text-sm font-medium transition-colors"
                >
                  {generating ? (
                    <span className="flex items-center justify-center gap-2">
                      <svg className="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                      </svg>
                      生成中...
                    </span>
                  ) : '1記事生成'}
                </button>
                <button
                  onClick={() => batchGenerate(3)}
                  disabled={generating}
                  className="flex-1 bg-[var(--surface2)] hover:bg-[var(--border)] border border-[var(--border)] disabled:opacity-40 text-[var(--text)] py-2.5 rounded-lg text-sm font-medium transition-colors"
                >
                  3記事まとめて
                </button>
              </div>

              {message && (
                <div className="text-xs p-3 bg-[var(--surface2)] border border-[var(--border)] rounded-lg text-[var(--subtle)] leading-relaxed">
                  {message}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Webhook Remote Control */}
        <WebhookPanel />

        {/* Logs table */}
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-[var(--border)] flex items-center justify-between">
            <h2 className="text-sm font-medium">実行ログ</h2>
            <span className="text-[10px] text-[var(--muted)] font-mono">最新 20件</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  {['エージェント', 'タスク', 'ステータス', '概要', '時間', '日時'].map((h) => (
                    <th key={h} className="px-4 py-2.5 text-left text-[10px] font-medium text-[var(--muted)] uppercase tracking-wider first:pl-5 last:pr-5 last:text-right">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]/50">
                {logs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-5 py-12 text-center text-[var(--muted)] text-sm">
                      ログがありません
                    </td>
                  </tr>
                )}
                {logs.map((l) => (
                  <tr key={l.id} className="hover:bg-[var(--surface2)] transition-colors">
                    <td className="px-4 py-3 pl-5 font-medium text-sm whitespace-nowrap">{l.agent_name}</td>
                    <td className="px-4 py-3 text-[var(--muted)] text-xs font-mono whitespace-nowrap">{l.task_type}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Badge status={l.status} />
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--muted)] max-w-xs truncate">
                      {l.output_summary || l.input_summary || l.error_message || '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--muted)] font-mono whitespace-nowrap">
                      {l.duration_ms ? `${(l.duration_ms / 1000).toFixed(1)}s` : '—'}
                    </td>
                    <td className="px-4 py-3 pr-5 text-right text-xs text-[var(--muted)] whitespace-nowrap">
                      {new Date(l.created_at).toLocaleString('ja-JP', {
                        month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit',
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </main>
    </div>
  )
}
