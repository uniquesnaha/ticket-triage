import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'

interface ProgressTrackerProps {
  fileName: string
}

export function ProgressTracker({ fileName }: ProgressTrackerProps) {
  return (
    <motion.div
      className="progress-card"
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.35 }}
    >
      <div className="progress-inner">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
        >
          <Loader2 size={36} className="progress-spinner" />
        </motion.div>
        <div className="progress-text">
          <p className="progress-title">Analyzing tickets…</p>
          <p className="progress-file">{fileName}</p>
        </div>
      </div>
      <div className="progress-bar-track">
        <motion.div
          className="progress-bar-fill"
          animate={{ x: ['0%', '60%', '0%'] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>
      <p className="progress-hint">
        Running preprocessing → LLM classification → guardrail checks
      </p>
    </motion.div>
  )
}
