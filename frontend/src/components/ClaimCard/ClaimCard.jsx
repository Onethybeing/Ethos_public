import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { verdictColor, verdictLabel } from '../../utils/helpers'
import styles from './ClaimCard.module.css'

const verdictBg = (verdict) => {
  if (verdict === 'supported')    return 'rgba(26,122,82,0.1)'
  if (verdict === 'contradicted') return 'rgba(200,40,30,0.1)'
  return 'rgba(181,131,10,0.1)'
}

export default function ClaimCard({ evaluation, index = 0 }) {
  const [open, setOpen] = useState(false)
  const { claim, verdict, confidence, evidence } = evaluation
  const normalizedVerdict = verdict === 'not-mentioned' ? 'unverified' : verdict

  const color = verdictColor(verdict)
  const label = verdictLabel(verdict)
  const bg    = verdictBg(verdict)

  return (
    <motion.div
      className={styles.card}
      style={{ '--verdict-color': color, '--verdict-bg': bg }}
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{
        delay: index * 0.08,
        type: 'spring',
        stiffness: 400,
        damping: 30,
      }}
    >
      {/* Header (clickable) */}
      <div className={styles.header} onClick={() => setOpen(!open)}>
        {/* Verdict Badge */}
        <div className={styles.verdictBadge}>
          {normalizedVerdict === 'supported' ? (
            <svg className={styles.checkIcon} viewBox="0 0 14 14">
              <motion.polyline
                className={styles.checkPath}
                points="2,7 5.5,10.5 12,3"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ delay: index * 0.08 + 0.3, duration: 0.4, ease: 'easeOut' }}
              />
            </svg>
          ) : (
            <div className={styles.verdictSquare} />
          )}
          {label}
        </div>

        {/* Claim text */}
        <div className={styles.claimText}>{claim}</div>

        {/* Confidence + chevron */}
        <div className={styles.right}>
          <div className={styles.confTrack}>
            <motion.div
              className={styles.confFill}
              initial={{ width: 0 }}
              animate={{ width: `${confidence * 100}%` }}
              transition={{ delay: index * 0.08 + 0.5, duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }}
            />
          </div>
          <span className={`${styles.chevron} ${open ? styles.open : ''}`}>▾</span>
        </div>
      </div>

      {/* Evidence (expandable) */}
      <AnimatePresence>
        {open && (
          <motion.div
            className={styles.evidence}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div className={styles.evidenceRule} />
            <div className={styles.evidenceText}>"{evidence}"</div>
            <div className={styles.confLine}>
              Confidence: {Math.round(confidence * 100)}%
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
