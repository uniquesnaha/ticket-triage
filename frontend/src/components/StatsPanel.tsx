import { motion } from 'framer-motion'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { TriageBatchResponse } from '../types/triage'
import { AlertTriangle, Users, Clock, Layers } from 'lucide-react'

interface StatsPanelProps {
  response: TriageBatchResponse
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#22d3ee',
}

const CATEGORY_COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#14b8a6',
  '#f59e0b', '#10b981', '#3b82f6', '#f43f5e', '#94a3b8',
]

export function StatsPanel({ response }: StatsPanelProps) {
  const priorityData = Object.entries(response.by_priority).map(([name, value]) => ({
    name,
    value,
    color: PRIORITY_COLORS[name] ?? '#6366f1',
  }))

  const categoryData = Object.entries(response.by_category).map(([name, value], i) => ({
    name: name.replace('_', ' '),
    value,
    color: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
  }))

  const statCards = [
    {
      icon: <Layers size={20} />,
      label: 'Total Tickets',
      value: response.total,
      color: 'var(--accent-indigo)',
    },
    {
      icon: <AlertTriangle size={20} />,
      label: 'Needs Review',
      value: response.needs_human_review_count,
      color: '#f97316',
    },
    {
      icon: <Users size={20} />,
      label: 'Critical Priority',
      value: response.by_priority['critical'] ?? 0,
      color: '#ef4444',
    },
    {
      icon: <Clock size={20} />,
      label: 'Processing Time',
      value: `${response.processing_time_ms}ms`,
      color: '#22d3ee',
    },
  ]

  return (
    <div className="stats-panel">
      {/* Stat Cards */}
      <div className="stat-cards">
        {statCards.map((card, i) => (
          <motion.div
            key={card.label}
            className="stat-card"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
          >
            <div className="stat-icon" style={{ color: card.color }}>{card.icon}</div>
            <div>
              <p className="stat-value" style={{ color: card.color }}>{card.value}</p>
              <p className="stat-label">{card.label}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Charts */}
      <div className="charts-row">
        <div className="chart-card">
          <h3 className="chart-title">By Priority</h3>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={priorityData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#1a1a24', border: '1px solid #2a2a38', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0' }}
                itemStyle={{ color: '#94a3b8' }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {priorityData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3 className="chart-title">By Category</h3>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={categoryData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#1a1a24', border: '1px solid #2a2a38', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0' }}
                itemStyle={{ color: '#94a3b8' }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {categoryData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Model info */}
      <div className="model-info">
        <span>Model: <strong>{response.model}</strong></span>
        <span>·</span>
        <span>Processed {response.total} ticket{response.total !== 1 ? 's' : ''}</span>
      </div>
    </div>
  )
}
