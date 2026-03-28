import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { getLeaderboard } from '../../api/client'
import { SkeletonRow } from '../../components/ui/Skeleton'
import styles from './Leaderboard.module.css'

const rowVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: (i) => ({
    opacity: 1,
    x: 0,
    transition: { delay: i * 0.055, type: 'spring', stiffness: 380, damping: 28 },
  }),
}

function RankSymbol({ rank }) {
  if (rank === 1) return <span className={`${styles.rank} ${styles.r1}`}>◆ 1</span>
  if (rank === 2) return <span className={`${styles.rank} ${styles.r2}`}>◇ 2</span>
  if (rank === 3) return <span className={`${styles.rank} ${styles.r3}`}>○ 3</span>
  return <span className={styles.rank}>{rank}</span>
}

export default function Leaderboard({ currentUserId = '' }) {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(false)

  useEffect(() => {
    getLeaderboard()
      .then(data => setEntries(data?.leaderboard ?? data ?? []))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [])

  const me = entries.find(e => e.user_id === currentUserId)
  const topScore = entries.length > 0 ? entries[0].score : 100

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--red)', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 10 }}>
          ■ Epistemic Rankings
        </div>
        <h1 className={styles.pageTitle}>The Epistemic Arena</h1>
        <p className={styles.subtitle}>
          Ranked by verified reading depth, claim evaluation accuracy, and source diversity.
        </p>
      </div>

      {/* My Score Card */}
      {me && (
        <motion.div
          className={styles.myScoreCard}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        >
          <div>
            <div className={styles.myScoreLabel}>■ Your Score</div>
            <motion.div
              className={styles.myScoreNum}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              {me.score.toFixed(1)}
            </motion.div>
          </div>
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--rule)', letterSpacing: '0.1em', textAlign: 'center' }}>
            {me.user_id}
            <div style={{ fontSize: 9, marginTop: 4, color: 'var(--rule)', opacity: 0.7 }}>
              {me.articles_read} articles · {me.claims_evaluated} claims
            </div>
          </div>
          <div className={styles.myRankWrap}>
            <div className={styles.myRankLabel}>■ Your Rank</div>
            <div className={styles.myRankNum}>
              #{entries.findIndex(e => e.user_id === currentUserId) + 1}
            </div>
          </div>
        </motion.div>
      )}

      {/* Table */}
      <div className={styles.table}>
        <div className={styles.tableHead}>
          <span>Rank</span>
          <span>Reader</span>
          <span style={{ textAlign: 'right' }}>Score</span>
        </div>

        {loading
          ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} />)
          : error
          ? <div style={{ fontFamily: 'var(--f-mono)', fontSize: 12, color: '#c8281e', padding: '24px 0' }}>■ Leaderboard unavailable — backend offline.</div>
          : entries.map((entry, i) => {
              const isMe = entry.user_id === currentUserId
              const pct = (entry.score / topScore) * 100

              return (
                <motion.div
                  key={entry.user_id}
                  className={`${styles.row} ${isMe ? styles.isMe : ''}`}
                  variants={rowVariants}
                  initial="hidden"
                  animate="visible"
                  custom={i}
                >
                  <RankSymbol rank={i + 1} />

                  <div className={styles.userInfo}>
                    <div className={styles.username}>
                      {entry.user_id}
                      {isMe && <span className={styles.youBadge}>YOU</span>}
                    </div>
                    <div className={styles.barTrack}>
                      <motion.div
                        className={styles.barFill}
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{
                          duration: 0.9,
                          delay: i * 0.07,
                          ease: [0.34, 1.56, 0.64, 1],
                        }}
                      />
                    </div>
                  </div>

                  <div className={styles.scoreCell}>
                    {entry.score.toFixed(1)}
                  </div>
                </motion.div>
              )
            })}
      </div>

      {/* Formula */}
      <div className={styles.formula}>
        <div className={styles.formulaLabel}>■ Scoring Formula</div>
        <div>Score = (0.4 × Depth) + (0.3 × Claim Accuracy) + (0.2 × Source Diversity) + (0.1 × Streak)</div>
        <div style={{ color: 'var(--ink-muted)', fontSize: 11, marginTop: 4 }}>
          Depth = normalized reading time per article · Claim Accuracy = fact-check engagement rate
        </div>
      </div>
    </div>
  )
}
