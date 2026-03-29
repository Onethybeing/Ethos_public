import { useEffect } from 'react'
import { motion, useSpring, useMotionValue, useTransform } from 'framer-motion'
import { slopColor, slopLabel } from '../../utils/helpers'
import styles from './SlopMeter.module.css'

export default function SlopMeter({ score }) {
  const hasScore = typeof score === 'number' && !Number.isNaN(score)
  const raw = useMotionValue(0)
  const spring = useSpring(raw, { stiffness: 100, damping: 22, restDelta: 0.001 })
  const needleLeft = useTransform(spring, [0, 1], ['0%', '100%'])
  const fillWidth  = useTransform(spring, [0, 1], ['0%', '100%'])

  useEffect(() => {
    const t = setTimeout(() => raw.set(hasScore ? score : 0), 120)
    return () => clearTimeout(t)
  }, [score, hasScore])

  const color = slopColor(score)
  const label = slopLabel(score)
  const pct   = hasScore ? Math.round(score * 100) : 'N/A'

  const statusLabel =
    !hasScore ? 'Insufficient Content for Reliable Analysis' :
    score < 0.3 ? 'Predominantly Human-Written' :
    score < 0.7 ? 'Mixed — Verify Claims Independently' :
                  'High AI-Generated Content Detected'

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <span>Content Integrity Analysis</span>
        <span className={styles.scoreNum} style={{ color }}>{hasScore ? `${pct}%` : pct}</span>
      </div>

      <div className={styles.trackOuter}>
        <div className={styles.trackGradient} />
        <motion.div className={styles.trackFill} style={{ width: fillWidth }} />
        <motion.div className={styles.needle} style={{ left: needleLeft }} />
      </div>

      <div className={styles.legend}>
        <span>Human Written</span>
        <span>AI Generated</span>
      </div>

      <div className={styles.statusLine} style={{ color }}>
        <div className={styles.statusDot} style={{ background: color }} />
        {statusLabel}
      </div>
    </div>
  )
}
