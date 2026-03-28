import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import SlopMeter from '../SlopMeter/SlopMeter'
import ClaimCard from '../ClaimCard/ClaimCard'
import ClusterViz from '../ClusterViz/ClusterViz'
import TerminalStream from '../ui/TerminalStream'
import Button from '../ui/Button'
import { factCheckArticle, getClusters, recordEvent, getArticle } from '../../api/client'
import { catColor, formatDate } from '../../utils/helpers'
import styles from './ArticlePanel.module.css'

const STREAM_LINES = [
  'Tokenizing article content...',
  'Extracting atomic factual claims...',
  'Querying evidence vectors in knowledge base...',
  'Running parallel LLM claim evaluations...',
  'Aggregating verdicts and confidence scores...',
]

const CLUSTER_LINES = [
  'Fetching article embedding from Qdrant...',
  'Retrieving 50 semantically similar articles...',
  'Running HDBSCAN narrative clustering...',
  'Generating pillar summaries with LLM...',
]

export default function ArticlePanel({ article, onClose }) {
  const [fcState,  setFcState]  = useState('idle')  // idle | loading | done
  const [fcData,   setFcData]   = useState(null)
  const [clState,  setClState]  = useState('idle')
  const [clData,   setClData]   = useState(null)
  const [content,  setContent]  = useState(article.content || null)
  const [contentLoading, setContentLoading] = useState(!article.content)
  const openTime = useRef(Date.now())

  // Fetch full article content if not already present
  useEffect(() => {
    if (article.content) return
    getArticle(article.id)
      .then(full => setContent(full?.content || ''))
      .catch(() => setContent(''))
      .finally(() => setContentLoading(false))
  }, [article.id])

  // Keyboard close + read-time tracking
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      const secs = Math.floor((Date.now() - openTime.current) / 1000)
      if (secs >= 5) recordEvent(article.id, secs)
    }
  }, [])

  async function runFactCheck() {
    setFcState('loading')
    try {
      const data = await factCheckArticle(article.id)
      setFcData(data)
      setFcState('done')
    } catch {
      setFcState('error')
    }
  }

  async function loadClusters() {
    setClState('loading')
    try {
      const data = await getClusters(article.id)
      setClData(data)
      setClState('done')
    } catch {
      setClState('error')
    }
  }

  const color = catColor(article.category)
  const verdictCounts = fcData ? {
    supported:    fcData.evaluations.filter(e => e.verdict === 'supported').length,
    contradicted: fcData.evaluations.filter(e => e.verdict === 'contradicted').length,
    unverified:   fcData.evaluations.filter(e => ['unverified','not-mentioned'].includes(e.verdict)).length,
  } : null

  return (
    <AnimatePresence>
      <>
        {/* Backdrop */}
        <motion.div
          className={styles.backdrop}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        />

        {/* Panel */}
        <motion.div
          className={styles.panel}
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', stiffness: 280, damping: 32 }}
        >
          {/* Close */}
          <div className={styles.closeRow}>
            <motion.button
              className={styles.closeBtn}
              onClick={onClose}
              whileHover={{ rotate: 90 }}
              transition={{ type: 'spring', stiffness: 500, damping: 20 }}
            >
              <X size={13} /> ESC
            </motion.button>
          </div>

          <div className={styles.content}>
            {/* Category color rule */}
            <div className={styles.catRule} style={{ background: color }} />

            {/* Title */}
            <h1 className={styles.title}>{article.title}</h1>

            {/* Dateline */}
            <div className={styles.dateline}>
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.sourceLink}
              >
                {article.source}
              </a>
              <span>—</span>
              <span>{formatDate(article.published_at)}</span>
            </div>

            {/* Slop Meter */}
            <SlopMeter score={article.ai_slop_score} />

            {/* Body */}
            <div className={styles.body}>
              {contentLoading
                ? <p className={styles.loadingText}>Loading article…</p>
                : content
                  ? content.split('\n').filter(Boolean).map((para, i) => <p key={i}>{para}</p>)
                  : <p className={styles.loadingText}>Content unavailable.</p>
              }
            </div>

            {/* ── Fact Check ── */}
            <div className={styles.sectionDiv}>
              <div className={styles.sectionHeavy} />
              <div className={styles.sectionLabel}>
                <div className={styles.sectionMark} />
                Fact Check
              </div>
              <div className={styles.sectionHeavy} />
            </div>

            {fcState === 'idle' && (
              <Button onClick={runFactCheck}>⚡ Run Fact Check</Button>
            )}
            {fcState === 'loading' && <TerminalStream lines={STREAM_LINES} />}
            {fcState === 'error' && <p className={styles.loadingText}>Fact check unavailable — backend error.</p>}
            {fcState === 'done' && fcData && (
              <>
                <div className={styles.fcSummary}>
                  <div className={styles.countBadge} style={{ color: '#1a7a52', borderColor: '#1a7a52' }}>
                    ■ {verdictCounts.supported} Supported
                  </div>
                  <div className={styles.countBadge} style={{ color: '#c8281e', borderColor: '#c8281e' }}>
                    ■ {verdictCounts.contradicted} Contradicted
                  </div>
                  <div className={styles.countBadge} style={{ color: '#b5830a', borderColor: '#b5830a' }}>
                    ■ {verdictCounts.unverified} Unverified
                  </div>
                </div>
                {fcData.evaluations.map((ev, i) => (
                  <ClaimCard key={i} evaluation={ev} index={i} />
                ))}
              </>
            )}

            {/* ── Narrative Clusters ── */}
            <div className={styles.sectionDiv} style={{ marginTop: 32 }}>
              <div className={styles.sectionHeavy} />
              <div className={styles.sectionLabel}>
                <div className={styles.sectionMark} />
                Narrative Clusters
              </div>
              <div className={styles.sectionHeavy} />
            </div>

            {clState === 'idle' && (
              <Button variant="secondary" onClick={loadClusters}>
                ⬡ Map Narrative Divergence
              </Button>
            )}
            {clState === 'loading' && <TerminalStream lines={CLUSTER_LINES} />}
            {clState === 'error' && <p className={styles.loadingText}>Cluster analysis unavailable — backend error.</p>}
            {clState === 'done' && <ClusterViz data={clData} />}

            <div style={{ height: 40 }} />
          </div>
        </motion.div>
      </>
    </AnimatePresence>
  )
}
