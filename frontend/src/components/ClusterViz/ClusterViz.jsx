import { motion } from 'framer-motion'
import { toRoman } from '../../utils/helpers'
import styles from './ClusterViz.module.css'

const PILLAR_COLORS = ['#2a4a8a', '#c8281e', '#6b3fa0']

export default function ClusterViz({ data }) {
  if (!data) return null
  const { pillars = [], noise_article_count = 0 } = data

  return (
    <div className={styles.wrap}>
      <div className={styles.pillarsGrid}>
        {pillars.map((pillar, i) => {
          const color = PILLAR_COLORS[i % PILLAR_COLORS.length]
          return (
            <motion.div
              key={pillar.cluster_id}
              className={styles.pillar}
              style={{ '--pillar-color': color }}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{
                delay: i * 0.1,
                type: 'spring',
                stiffness: 340,
                damping: 28,
              }}
            >
              <div
                className={styles.pillarTopRule}
                style={{ background: color }}
              />
              <div className={styles.pillarHead}>
                <span className={styles.pillarNum}>
                  Column {toRoman(i + 1)}
                </span>
                <span className={styles.pillarCount}>
                  {pillar.article_count} art.
                </span>
              </div>
              <p className={styles.pillarSummary}>{pillar.summary}</p>
              <div className={styles.divRow}>
                <span className={styles.divLabel}>Divergence</span>
                <div className={styles.divTrack}>
                  <motion.div
                    className={styles.divFill}
                    initial={{ width: 0 }}
                    whileInView={{ width: `${Math.min(pillar.divergence_score * 100, 100)}%` }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.1 + 0.3, duration: 0.7, ease: [0.34, 1.56, 0.64, 1] }}
                  />
                </div>
                <span className={styles.divVal}>{pillar.divergence_score.toFixed(3)}</span>
              </div>
            </motion.div>
          )
        })}
      </div>
      {noise_article_count > 0 && (
        <div className={styles.noiseNote}>
          {noise_article_count} unclustered articles excluded from analysis
        </div>
      )}
    </div>
  )
}
