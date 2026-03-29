import { useState, useEffect, useRef } from 'react'
import { motion as Motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import SlopMeter from '../SlopMeter/SlopMeter'
import ClaimCard from '../ClaimCard/ClaimCard'
import ClusterViz from '../ClusterViz/ClusterViz'
import TerminalStream from '../ui/TerminalStream'
import Button from '../ui/Button'
import { factCheckArticle, getClusters, recordEvent, getArticle, getRephrase, getEngagementStatus, getVoice } from '../../api/client'
import { catColor, formatDate } from '../../utils/helpers'
import EngagementBar from './EngagementBar'
import CommentSection from './CommentSection'
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

const VOICE_LINES = [
  'Analysing article content...',
  'Crafting narration script...',
  'Sending to Groq TTS engine...',
  'Synthesising speech waveform...',
]

const VOICE_MODE_OPTS = [
  { id: 'anchor',  label: 'News Anchor',    icon: '📺' },
  { id: 'podcast', label: 'Casual Podcast', icon: '🎙' },
  { id: 'drama',   label: 'Breaking Drama', icon: '⚡' },
]

export default function ArticlePanel({ article, onClose }) {
  const [fcState, setFcState] = useState('idle')  // idle | loading | slow | done | error
  const [fcData, setFcData] = useState(null)
  const [clState, setClState] = useState('idle')
  const [clData, setClData] = useState(null)
  const [rpState, setRpState] = useState('idle')
  const [rpData, setRpData] = useState(null)
  const [showRephrased, setShowRephrased] = useState(false)
  const [content, setContent] = useState(article.content || article.excerpt || null)
  const [contentLoading, setContentLoading] = useState(!article.content)
  const [hasRead, setHasRead] = useState(true)
  const [voiceMode, setVoiceMode] = useState('anchor')
  const [voiceState, setVoiceState] = useState('idle')  // idle | loading | done | error
  const [voiceData, setVoiceData] = useState(null)      // { script, label }
  const [isPlaying, setIsPlaying] = useState(false)
  const utteranceRef = useRef(null)
  const openTime = useRef(Date.now())
  const fcSlowTimer = useRef(null)

  useEffect(() => {
    setContent(article.content || article.excerpt || null)
    setContentLoading(!article.content)

    if (article.content) return

    let cancelled = false

    getArticle(article.id)
      .then(full => {
        if (cancelled) return
        setContent(full?.content || article.excerpt || '')
      })
      .catch(() => {
        if (cancelled) return
        if (!article.excerpt) setContent('')
      })
      .finally(() => {
        if (!cancelled) setContentLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [article.id, article.content, article.excerpt])

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    const openedAt = openTime.current
    document.addEventListener('keydown', onKey)

    // Initial check for read status (we can still track it for analytics)
    getEngagementStatus(article.id).then(status => setHasRead(status.has_read || true))

    return () => {
      document.removeEventListener('keydown', onKey)
      const secs = Math.floor((Date.now() - openedAt) / 1000)
      if (secs >= 5) recordEvent(article.id, secs)
    }
  }, [article.id, onClose])

  // Stop speech when panel closes
  useEffect(() => {
    return () => window.speechSynthesis.cancel()
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

  async function loadVoice() {
    // Stop any ongoing speech
    window.speechSynthesis.cancel()
    setIsPlaying(false)
    setVoiceData(null)
    setVoiceState('loading')
    try {
      const data = await getVoice(article.id, voiceMode)
      setVoiceData(data)
      setVoiceState('done')
    } catch {
      setVoiceState('error')
    }
  }

  function togglePlay() {
    if (isPlaying) {
      window.speechSynthesis.pause()
      setIsPlaying(false)
    } else if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume()
      setIsPlaying(true)
    } else if (voiceData?.script) {
      const utter = new SpeechSynthesisUtterance(voiceData.script)
      // Tune delivery per mode
      if (voiceMode === 'anchor') {
        utter.rate = 0.95; utter.pitch = 1.0
      } else if (voiceMode === 'podcast') {
        utter.rate = 1.1; utter.pitch = 1.1
      } else {
        utter.rate = 0.88; utter.pitch = 0.85
      }
      utter.onend = () => setIsPlaying(false)
      utter.onerror = () => setIsPlaying(false)
      utteranceRef.current = utter
      window.speechSynthesis.speak(utter)
      setIsPlaying(true)
    }
  }

  const color = catColor(article.category)
  const verdictCounts = fcData ? {
    supported: fcData.evaluations.filter(e => e.verdict === 'supported').length,
    contradicted: fcData.evaluations.filter(e => e.verdict === 'contradicted').length,
    unverified: fcData.evaluations.filter(e => ['unverified', 'not-mentioned'].includes(e.verdict)).length,
  } : null

  return (
    <AnimatePresence>
      <>
        {/* Backdrop */}
        <Motion.div
          className={styles.backdrop}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        />

        {/* Full-screen panel */}
        <Motion.div
          className={styles.panel}
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98 }}
          transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
        >
          {/* Sticky close bar */}
          <div className={styles.closeRow}>
            <Motion.button
              className={styles.closeBtn}
              onClick={onClose}
              whileHover={{ rotate: 90 }}
              transition={{ type: 'spring', stiffness: 500, damping: 20 }}
            >
              <X size={13} /> ESC
            </Motion.button>
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
              <EngagementBar articleId={article.id} hasRead={hasRead} />

              {/* Article body */}
              <div className={styles.body}>
                {showRephrased && rpData
                  ? rpData.rephrased_content.split('\n').filter(Boolean).map((para, i) => <p key={i}>{para}</p>)
                  : content
                    ? content.split('\n').filter(Boolean).map((para, i) => <p key={i}>{para}</p>)
                    : contentLoading
                      ? <p className={styles.loadingText}>Loading article…</p>
                      : <p className={styles.loadingText}>Content unavailable.</p>
                }

                {!showRephrased && contentLoading && content && (
                  <p className={styles.loadingText}>Loading full article…</p>
                )}
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

              {/* Discussion Section */}
              <CommentSection articleId={article.id} hasRead={hasRead} />
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
                        <Motion.div
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

              {/* ── Voice ── */}
              <div className={styles.sectionDiv} style={{ marginTop: 32 }}>
                <div className={styles.sectionHeavy} />
                <div className={styles.sectionLabel}>
                  <div className={styles.sectionMark} />
                  Listen
                </div>
                <div className={styles.sectionHeavy} />
              </div>

              {/* Mode picker */}
              <div className={styles.voiceModes}>
                {VOICE_MODE_OPTS.map(opt => (
                  <button
                    key={opt.id}
                    className={`${styles.toggleBtn} ${voiceMode === opt.id ? styles.active : ''}`}
                    onClick={() => {
                      setVoiceMode(opt.id)
                      // Reset so user can regenerate in the new mode
                      if (voiceState === 'done') setVoiceState('idle')
                    }}
                    disabled={voiceState === 'loading'}
                    title={opt.label}
                  >
                    {opt.icon} {opt.label}
                  </button>
                ))}
              </div>

              {voiceState === 'idle' && (
                <Button onClick={loadVoice}>▶ Generate Audio</Button>
              )}
              {voiceState === 'loading' && <TerminalStream lines={VOICE_LINES} />}
              {voiceState === 'error' && (
                <p className={styles.loadingText}>Voice unavailable — try again.</p>
              )}
              {voiceState === 'done' && voiceData && (
                <>
                  <div style={{
                    border: '1px solid var(--rule)',
                    padding: '12px 14px',
                    marginBottom: 12,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                      <Motion.button
                        onClick={togglePlay}
                        style={{
                          width: 34, height: 34,
                          background: 'var(--ink)',
                          color: 'var(--paper)',
                          border: 'none',
                          cursor: 'pointer',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontFamily: 'var(--f-mono)',
                          fontSize: 14,
                          flexShrink: 0,
                        }}
                        whileTap={{ scale: 0.92 }}
                        whileHover={{ opacity: 0.8 }}
                      >
                        {isPlaying ? '⏸' : '▶'}
                      </Motion.button>
                      <div>
                        <div style={{
                          fontFamily: 'var(--f-mono)',
                          fontSize: 9,
                          fontWeight: 700,
                          letterSpacing: '0.15em',
                          textTransform: 'uppercase',
                          color: 'var(--ink-muted)',
                        }}>
                          {voiceData.label}
                        </div>
                        <div style={{
                          fontFamily: 'var(--f-mono)',
                          fontSize: 10,
                          color: 'var(--ink-muted)',
                          marginTop: 2,
                        }}>
                          {isPlaying ? '● PLAYING' : '○ PAUSED'}
                        </div>
                      </div>
                      <button
                        onClick={loadVoice}
                        style={{
                          marginLeft: 'auto',
                          fontFamily: 'var(--f-mono)',
                          fontSize: 9,
                          letterSpacing: '0.1em',
                          textTransform: 'uppercase',
                          color: 'var(--ink-muted)',
                          background: 'none',
                          border: '1px solid var(--rule)',
                          padding: '4px 8px',
                          cursor: 'pointer',
                        }}
                        title="Regenerate"
                      >
                        ↺
                      </button>
                    </div>
                    {/* Script transcript */}
                    <div style={{
                      fontFamily: 'var(--f-mono)',
                      fontSize: 10,
                      color: 'var(--ink-muted)',
                      lineHeight: 1.7,
                      borderTop: '1px solid var(--rule)',
                      paddingTop: 10,
                      letterSpacing: '0.02em',
                    }}>
                      {voiceData.script}
                    </div>
                  </div>
                </>
              )}

              <div style={{ height: 40 }} />
            </div>
          </div>
        </Motion.div>
      </>
    </AnimatePresence >
  )
}
