import { motion } from 'framer-motion'
import { catColor, slopColor, slopLabel, timeAgo } from '../../utils/helpers'
import styles from './FeedCard.module.css'

function looksLikeUrl(value = '') {
  return /^(https?:\/\/|www\.)\S+$/i.test(value.trim())
}

function normalizeText(value = '') {
  return value.replace(/\s+/g, ' ').trim()
}

function getPreviewText(article) {
  const candidates = [
    article.excerpt,
    article.summary,
    article.description,
    article.content,
    article.body,
  ]

  for (const candidate of candidates) {
    if (typeof candidate !== 'string') continue
    const cleaned = normalizeText(candidate)
    if (!cleaned || looksLikeUrl(cleaned)) continue
    return cleaned
  }

  return ''
}

function getSourceLabel(source = '') {
  if (typeof source !== 'string') return ''
  const cleaned = source.trim()
  if (!cleaned) return ''
  if (!looksLikeUrl(cleaned)) return cleaned

  try {
    const parsed = new URL(cleaned.startsWith('http') ? cleaned : `https://${cleaned}`)
    return parsed.hostname.replace(/^www\./i, '')
  } catch {
    return cleaned.replace(/^https?:\/\//i, '').replace(/^www\./i, '')
  }
}

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: (i) => ({
    opacity: 1, y: 0,
    transition: { type: 'spring', stiffness: 360, damping: 28, delay: i * 0.055 },
  }),
}

export default function FeedCard({ article, index = 0, featured = false, onClick, onHover }) {
  const hasSlopScore = typeof article.ai_slop_score === 'number' && !Number.isNaN(article.ai_slop_score)
  const cc = catColor(article.category)
  const sc = slopColor(article.ai_slop_score)
  const sl = slopLabel(article.ai_slop_score)
  const pct = hasSlopScore ? Math.round(article.ai_slop_score * 100) : 'N/A'
  const previewText = getPreviewText(article)
  const sourceLabel = getSourceLabel(article.source)

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
      onMouseEnter={onHover}
      onClick={onClick}
    >
      {/* Category Stamp */}
      <div className={styles.categoryStamp}>
        <div className={styles.categorySquare} />
        {article.category}
      </div>

      {/* Title */}
      <h2 className={styles.title}>{article.title}</h2>

      {/* Excerpt */}
      {previewText && <p className={styles.excerpt}>{previewText}</p>}

      {/* Byline */}
      <div className={styles.byline}>
        {sourceLabel && <span>{sourceLabel}</span>}
        {sourceLabel && article.published_at && <span className={styles.bylineDot}>·</span>}
        {article.published_at && <span>{timeAgo(article.published_at)}</span>}
      </div>

      {/* Trending Indicator (optional/dynamic) */}
      {(article.upvotes > 0 || article.downvotes > 0) && (
        <div className={styles.voteSummary}>
          <span className={styles.upCount}>▲ {article.upvotes}</span>
          <span className={styles.downCount}>▼ {article.downvotes}</span>
        </div>
      )}

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
