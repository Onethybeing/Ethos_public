import { motion } from 'framer-motion'
import { catColor, slopColor, slopLabel, timeAgo } from '../../utils/helpers'
import styles from './FeedCard.module.css'

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: (i) => ({
    opacity: 1, y: 0,
    transition: { type: 'spring', stiffness: 360, damping: 28, delay: i * 0.055 },
  }),
}

export default function FeedCard({ article, index = 0, featured = false, onClick }) {
  const hasSlopScore = typeof article.ai_slop_score === 'number' && !Number.isNaN(article.ai_slop_score)
  const cc = catColor(article.category)
  const sc = slopColor(article.ai_slop_score)
  const sl = slopLabel(article.ai_slop_score)
  const pct = hasSlopScore ? Math.round(article.ai_slop_score * 100) : 'N/A'

  return (
    <motion.article
      className={`${styles.card} ${featured ? styles.featured : ''}`}
      style={{ '--cat-color': cc, '--seal-color': sc }}
      variants={cardVariants}
      custom={index}
      initial="hidden"
      animate="visible"
      whileHover={{
        x: 4,
        boxShadow: '4px 4px 0px var(--red)',
        transition: { type: 'spring', stiffness: 600, damping: 30 },
      }}
      whileTap={{ scale: 0.99 }}
      onClick={onClick}
    >
      {/* Category Stamp */}
      <div className={styles.categoryStamp}>
        <div className={styles.categorySquare} />
        {article.category}
      </div>

      {/* Title */}
      <h2 className={styles.title}>{article.title}</h2>

      {/* Byline */}
      <div className={styles.byline}>
        <span>{article.source}</span>
        <span className={styles.bylineDot}>·</span>
        <span>{timeAgo(article.published_at)}</span>
      </div>

      {/* Excerpt */}
      <p className={styles.excerpt}>{article.content}</p>

      {/* Footer */}
      <div className={styles.footer}>
        <div className={styles.integritySeal}>
          <span className={styles.sealScore}>
            {sl === 'Human' ? '●' : sl === 'Mixed' ? '◑' : sl === 'AI Slop' ? '○' : '·'} {hasSlopScore ? `${pct}%` : pct}
          </span>
          <span className={styles.sealLabel}>{sl}</span>
        </div>
        <span className={styles.readMore}>Read →</span>
      </div>
    </motion.article>
  )
}
