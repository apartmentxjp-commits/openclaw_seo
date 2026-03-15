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
      setMessage(`✅ ${data.message} (Log ID: ${data.log_id?.slice(0, 8)}...)`)
      setTimeout(fetchStatus, 3000)
    } catch (e) {
      setMessage('❌ エラーが発生しました')
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
      setMessage(`✅ ${data.message}`)
      setTimeout(fetchStatus, 5000)
    } catch {
      setMessage('❌ エラーが発生しました')
    } finally {
      setGenerating(false)
    }
  }

  const statusColor = (s: string) => {
    if (s === 'success') return 'text-green-600 bg-green-50'
    if (s === 'error') return 'text-red-600 bg-red-50'
    return 'text-yellow-600 bg-yellow-50'
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display text-2xl font-bold">AIエージェント 管理ダッシュボード</h1>
          <p className="text-muted text-sm mt-1">Gemini AI エージェントの制御・監視</p>
        </div>
        <button
          onClick={fetchStatus}
          className="text-xs border border-ink/20 px-3 py-1.5 rounded hover:bg-ink/5 transition-colors"
        >
          🔄 更新
        </button>
      </div>

      {/* Stats Cards */}
      {status && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: '公開記事数', value: status.total_articles, icon: '📄' },
            { label: '24h成功', value: status.last_24h?.success_count || 0, icon: '✅' },
            { label: '24h エラー', value: status.last_24h?.error_count || 0, icon: '❌' },
            { label: '実行中', value: status.last_24h?.running_count || 0, icon: '⏳' },
          ].map((s) => (
            <div key={s.label} className="border border-ink/10 rounded-lg p-4 bg-paper">
              <div className="text-2xl mb-1">{s.icon}</div>
              <div className="font-display text-2xl font-bold">{s.value}</div>
              <div className="text-xs text-muted">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6 mb-8">
        {/* エージェント一覧 */}
        <div className="border border-ink/10 rounded-lg p-5 bg-paper">
          <h2 className="font-medium mb-4">🤖 常駐エージェント</h2>
          {status ? (
            <div className="space-y-3">
              {Object.entries(status.agents).map(([key, agent]) => (
                <div key={key} className="flex items-center justify-between text-sm p-3 bg-ink/[0.03] rounded">
                  <div>
                    <span className="font-medium capitalize">{key}</span>
                    <span className="text-muted text-xs ml-2">{agent.role}</span>
                  </div>
                  <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded">
                    稼働中 · {agent.model}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted text-sm">接続中...</p>
          )}
        </div>

        {/* 記事生成フォーム */}
        <div className="border border-ink/10 rounded-lg p-5 bg-paper">
          <h2 className="font-medium mb-4">✍️ 記事を今すぐ生成</h2>
          <div className="space-y-3 mb-4">
            <div>
              <label className="text-xs text-muted mb-1 block">都道府県</label>
              <input
                value={form.prefecture}
                onChange={(e) => setForm({ ...form, prefecture: e.target.value })}
                className="w-full border border-ink/20 rounded px-3 py-2 text-sm focus:outline-none focus:border-ink/40"
              />
            </div>
            <div>
              <label className="text-xs text-muted mb-1 block">エリア</label>
              <input
                value={form.area}
                onChange={(e) => setForm({ ...form, area: e.target.value })}
                className="w-full border border-ink/20 rounded px-3 py-2 text-sm focus:outline-none focus:border-ink/40"
              />
            </div>
            <div>
              <label className="text-xs text-muted mb-1 block">物件種別</label>
              <select
                value={form.property_type}
                onChange={(e) => setForm({ ...form, property_type: e.target.value })}
                className="w-full border border-ink/20 rounded px-3 py-2 text-sm focus:outline-none focus:border-ink/40"
              >
                {['マンション', '一戸建て', '土地'].map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={generateArticle}
              disabled={generating}
              className="flex-1 bg-accent hover:bg-accent/90 disabled:opacity-50 text-white py-2 rounded text-sm font-medium transition-colors"
            >
              {generating ? '生成中...' : '1記事生成'}
            </button>
            <button
              onClick={() => batchGenerate(3)}
              disabled={generating}
              className="flex-1 bg-ink hover:bg-ink/80 disabled:opacity-50 text-white py-2 rounded text-sm font-medium transition-colors"
            >
              3記事まとめて
            </button>
          </div>
          {message && (
            <p className="mt-3 text-sm p-3 bg-ink/5 rounded">{message}</p>
          )}
        </div>
      </div>

      {/* Agent Logs */}
      <div className="border border-ink/10 rounded-lg bg-paper">
        <div className="px-5 py-4 border-b border-ink/10">
          <h2 className="font-medium">📋 実行ログ (最新20件)</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink/10 text-xs text-muted">
                <th className="px-4 py-2 text-left">エージェント</th>
                <th className="px-4 py-2 text-left">タスク</th>
                <th className="px-4 py-2 text-left">ステータス</th>
                <th className="px-4 py-2 text-left hidden md:table-cell">入力</th>
                <th className="px-4 py-2 text-right hidden md:table-cell">時間</th>
                <th className="px-4 py-2 text-right">日時</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-muted">ログがありません</td>
                </tr>
              )}
              {logs.map((l) => (
                <tr key={l.id} className="border-t border-ink/5 hover:bg-ink/[0.02]">
                  <td className="px-4 py-2 font-medium">{l.agent_name}</td>
                  <td className="px-4 py-2 text-muted text-xs">{l.task_type}</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs px-2 py-0.5 rounded ${statusColor(l.status)}`}>
                      {l.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-xs text-muted hidden md:table-cell max-w-xs truncate">
                    {l.input_summary || l.output_summary || l.error_message || '-'}
                  </td>
                  <td className="px-4 py-2 text-right text-xs text-muted hidden md:table-cell">
                    {l.duration_ms ? `${l.duration_ms}ms` : '-'}
                  </td>
                  <td className="px-4 py-2 text-right text-xs text-muted">
                    {new Date(l.created_at).toLocaleString('ja-JP', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
