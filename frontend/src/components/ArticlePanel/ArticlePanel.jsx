import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import SlopMeter from '../SlopMeter/SlopMeter'
import ClaimCard from '../ClaimCard/ClaimCard'
import ClusterViz from '../ClusterViz/ClusterViz'
import TerminalStream from '../ui/TerminalStream'
import Button from '../ui/Button'
import { factCheckArticle, getClusters, recordEvent, getArticle, getRephrase } from '../../api/client'
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

const REPHRASE_LINES = [
  'Parsing article structure...',
  'Applying lexical substitution model...',
  'Preserving factual claims and named entities...',
  'Validating length and fidelity constraints...',
]

export default function ArticlePanel({ article, onClose }) {
  const [fcState,       setFcState]       = useState('idle')  // idle | loading | slow | done | error
  const [fcData,        setFcData]        = useState(null)
  const [clState,       setClState]       = useState('idle')
  const [clData,        setClData]        = useState(null)
  const [rpState,       setRpState]       = useState('idle')
  const [rpData,        setRpData]        = useState(null)
  const [showRephrased, setShowRephrased] = useState(false)
  const [content,       setContent]       = useState(article.content || null)
  const [contentLoading, setContentLoading] = useState(!article.content)
  const openTime = useRef(Date.now())
  const fcSlowTimer = useRef(null)

  useEffect(() => {
    if (article.content) return
    getArticle(article.id)
      .then(full => setContent(full?.content || ''))
      .catch(() => setContent(''))
      .finally(() => setContentLoading(false))
  }, [article.id])

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
    // After 20s still loading → show "still processing" message instead of erroring
    fcSlowTimer.current = setTimeout(() => setFcState('slow'), 20_000)
    try {
      const data = await factCheckArticle(article.id)
      setFcData(data)
      setFcState('done')
    } catch {
      setFcState('error')
    } finally {
      clearTimeout(fcSlowTimer.current)
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

  async function loadRephrase() {
    setRpState('loading')
    try {
      const data = await getRephrase(article.id)
      setRpData(data)
      setRpState('done')
    } catch {
      setRpState('error')
    }
  }

  const color = catColor(article.category)
  const verdictCounts = fcData ? {
    supported:    fcData.evaluations.filter(e => e.verdict === 'supported').length,
    contradicted: fcData.evaluations.filter(e => e.verdict === 'contradicted').length,
    unverified:   fcData.evaluations.filter(e => ['unverified', 'not-mentioned'].includes(e.verdict)).length,
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

        {/* Full-screen panel */}
        <motion.div
          className={styles.panel}
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98 }}
          transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
        >
          {/* Sticky close bar */}
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

          {/* Two-column reader layout */}
          <div className={styles.readerLayout}>

            {/* ── Left: reading column ── */}
            <div className={styles.readingColumn}>
              <div className={styles.catRule} style={{ background: color }} />

              <h1 className={styles.title}>{article.title}</h1>

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

              {/* Toggle bar — shown only after rephrase loads */}
              {rpState === 'done' && rpData && (
                <div className={styles.toggleBar}>
                  <button
                    className={`${styles.toggleBtn} ${!showRephrased ? styles.active : ''}`}
                    onClick={() => setShowRephrased(false)}
                  >
                    Original
                  </button>
                  <button
                    className={`${styles.toggleBtn} ${showRephrased ? styles.active : ''}`}
                    onClick={() => setShowRephrased(true)}
                  >
                    Rephrased
                  </button>
                </div>
              )}

              {/* Article body */}
              <div className={styles.body}>
                {contentLoading
                  ? <p className={styles.loadingText}>Loading article…</p>
                  : showRephrased && rpData
                    ? rpData.rephrased_content.split('\n').filter(Boolean).map((para, i) => <p key={i}>{para}</p>)
                    : content
                      ? content.split('\n').filter(Boolean).map((para, i) => <p key={i}>{para}</p>)
                      : <p className={styles.loadingText}>Content unavailable.</p>
                }
              </div>

              {/* Rephrased footer */}
              {showRephrased && rpData && (
                <div className={styles.rephrasedFooter}>
                  To read the full article, open this link to the original source:{' '}
                  <a href={rpData.source_url} target="_blank" rel="noopener noreferrer">
                    {article.source}
                  </a>
                </div>
              )}
            </div>

            {/* ── Right: analysis rail ── */}
            <div className={styles.rail}>
              <SlopMeter score={article.ai_slop_score} />

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
              {(fcState === 'loading' || fcState === 'slow') && (
                <>
                  <TerminalStream lines={STREAM_LINES} />
                  {fcState === 'slow' && (
                    <p className={styles.loadingText} style={{ marginTop: 8 }}>
                      Still processing — LLM is evaluating claims in parallel…
                    </p>
                  )}
                </>
              )}
              {fcState === 'error' && (
                <p className={styles.loadingText}>Fact check unavailable — backend error.</p>
              )}
              {fcState === 'done' && fcData && (
                <>
                  {/* Verdict counts */}
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

                  {/* Confidence histogram */}
                  <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 32, margin: '10px 0 4px' }}>
                    {fcData.evaluations.map((ev, i) => {
                      const barColor = ev.verdict === 'supported' ? '#1a7a52'
                        : ev.verdict === 'contradicted' ? '#c8281e' : '#b5830a'
                      return (
                        <motion.div
                          key={i}
                          title={`${ev.claim.slice(0, 60)}… — ${Math.round(ev.confidence * 100)}%`}
                          style={{ flex: 1, background: barColor, opacity: 0.75, borderRadius: 1 }}
                          initial={{ height: 0 }}
                          animate={{ height: `${Math.max(ev.confidence * 32, 4)}px` }}
                          transition={{ delay: i * 0.05, duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
                        />
                      )
                    })}
                  </div>
                  <div style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--ink-muted)', marginBottom: 12 }}>
                    Evidence confidence per claim
                  </div>

                  {/* Slop correlation alert */}
                  {fcData.unverifiable_ratio >= 0.5 && fcData.slop_score >= 0.5 && (
                    <div style={{
                      fontFamily: 'var(--f-mono)',
                      fontSize: 11,
                      color: '#c8281e',
                      border: '1px solid #c8281e',
                      padding: '8px 10px',
                      marginBottom: 12,
                      lineHeight: 1.5,
                    }}>
                      ■ HIGH INTEGRITY CONCERN — {Math.round(fcData.unverifiable_ratio * 100)}% of claims unverifiable
                      + AI slop score {Math.round(fcData.slop_score * 100)}%. Treat with caution.
                    </div>
                  )}

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
              {clState === 'error' && (
                <p className={styles.loadingText}>Cluster analysis unavailable — backend error.</p>
              )}
              {clState === 'done' && <ClusterViz data={clData} />}

              {/* ── Rephrase ── */}
              <div className={styles.sectionDiv} style={{ marginTop: 32 }}>
                <div className={styles.sectionHeavy} />
                <div className={styles.sectionLabel}>
                  <div className={styles.sectionMark} />
                  Rephrase
                </div>
                <div className={styles.sectionHeavy} />
              </div>

              {rpState === 'idle' && (
                <Button variant="secondary" onClick={loadRephrase}>
                  ⟳ Show Rephrased Version
                </Button>
              )}
              {rpState === 'loading' && <TerminalStream lines={REPHRASE_LINES} />}
              {rpState === 'error' && (
                <p className={styles.loadingText}>Rephrase unavailable — backend error.</p>
              )}
              {rpState === 'done' && rpData && (
                <Button
                  variant={showRephrased ? 'primary' : 'secondary'}
                  onClick={() => setShowRephrased(r => !r)}
                >
                  {showRephrased ? '← Show Original' : '⟳ Show Rephrased Version'}
                </Button>
              )}

              <div style={{ height: 40 }} />
            </div>
          </div>
        </motion.div>
      </>
    </AnimatePresence>
  )
}
