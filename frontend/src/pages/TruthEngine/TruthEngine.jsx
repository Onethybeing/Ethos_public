import { Component, Suspense, lazy, useMemo, useRef, useState } from 'react'
import Button from '../../components/ui/Button'
import { factCheckText } from '../../api/client'
import styles from './TruthEngine.module.css'

const ClaimCard = lazy(() => import('../../components/ClaimCard/ClaimCard'))
const TerminalStream = lazy(() => import('../../components/ui/TerminalStream'))

const PAGE_SIZE = 5

class SectionErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch() {
    // Contain UI failures locally so the rest of Truth Engine remains usable.
  }

  render() {
    if (this.state.hasError) {
      return (
        <p style={{ fontFamily: 'var(--f-mono)', fontSize: 12, color: '#c8281e', marginTop: 16 }}>
          ■ {this.props.fallbackText || 'Section unavailable.'}
        </p>
      )
    }
    return this.props.children
  }
}

function normalizeVerdict(value = '') {
  const verdict = String(value).toLowerCase()
  if (verdict === 'supported') return 'supported'
  if (verdict === 'contradicted') return 'contradicted'
  return 'not-mentioned'
}

function normalizeEvaluation(evaluation = {}) {
  const verdict = normalizeVerdict(evaluation.verdict ?? evaluation.classification)
  const confidence = Number(evaluation.confidence)
  return {
    claim: evaluation.claim ?? 'Unknown claim',
    verdict,
    confidence: Number.isFinite(confidence)
      ? Math.min(Math.max(confidence, 0), 1)
      : (verdict === 'not-mentioned' ? 0.5 : 0.75),
    evidence: evaluation.evidence ?? evaluation.explanation ?? 'No evidence text returned.',
    supporting_urls: Array.isArray(evaluation.supporting_urls) ? evaluation.supporting_urls : [],
  }
}

function normalizeFactCheckPayload(payload = {}) {
  const source = payload.result ?? payload
  const evaluations = Array.isArray(source.evaluations)
    ? source.evaluations.map(normalizeEvaluation)
    : []

  return { evaluations }
}

function extractErrorMessage(error) {
  const status = error?.response?.status
  const payload = error?.response?.data
  let detail = ''

  if (typeof payload === 'string') {
    detail = payload
  } else if (typeof payload?.detail === 'string') {
    detail = payload.detail
  } else if (Array.isArray(payload?.detail)) {
    detail = payload.detail.map(item => item?.msg).filter(Boolean).join('; ')
  }

  if (status) {
    return `Verification pipeline failed on backend (HTTP ${status})${detail ? ` — ${detail}` : '.'}`
  }

  if (error?.code === 'ECONNABORTED') {
    return 'Verification timed out — backend took too long to respond.'
  }

  return 'Verification failed — backend unavailable.'
}

const STREAM_LINES = [
  'Tokenizing input document...',
  'Extracting atomic factual claims...',
  'Querying evidence vectors in knowledge base...',
  'Running parallel LLM claim evaluations...',
  'Aggregating verdicts and confidence scores...',
]

const SAMPLES = [
  'The James Webb Space Telescope launched on Dec 25 2021 and cost approximately $10 billion. It operates at the L2 Lagrange point, 1.5 million km from Earth.',
  'Bitcoin has a hard cap of 21 million coins. The last Bitcoin is estimated to be mined around the year 2140 due to the halving mechanism.',
]

export default function TruthEngine() {
  const [text,    setText]    = useState('')
  const [state,   setState]   = useState('idle')
  const [results, setResults] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [page, setPage] = useState(1)
  const requestIdRef = useRef(0)

  const evaluations = useMemo(
    () => (Array.isArray(results?.evaluations) ? results.evaluations : []),
    [results]
  )

  const counts = useMemo(() => {
    if (!results) return null
    return {
      supported:    evaluations.filter(e => e.verdict === 'supported').length,
      contradicted: evaluations.filter(e => e.verdict === 'contradicted').length,
      unverified:   evaluations.filter(e => ['unverified', 'not-mentioned'].includes(e.verdict)).length,
    }
  }, [evaluations, results])

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(evaluations.length / PAGE_SIZE)),
    [evaluations.length]
  )

  const safePage = Math.min(page, totalPages)

  const paginatedEvaluations = useMemo(() => {
    const start = (safePage - 1) * PAGE_SIZE
    return evaluations.slice(start, start + PAGE_SIZE)
  }, [evaluations, safePage])

  async function runCheck() {
    if (!text.trim()) return
    const requestId = ++requestIdRef.current
    setState('loading')
    setResults(null)
    setErrorMessage('')
    setPage(1)
    try {
      const data = normalizeFactCheckPayload(await factCheckText(text))
      if (requestId !== requestIdRef.current) return
      setResults(data)
      setState('done')
    } catch (error) {
      if (requestId !== requestIdRef.current) return
      setErrorMessage(extractErrorMessage(error))
      setState('error')
    }
  }

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.volumeLine}>
          <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-muted)', letterSpacing: '0.1em' }}>
            ■ VERIFICATION DESK
          </span>
        </div>
        <div className={styles.rule1} />
        <div className={styles.titleRow}>
          <h1 className={styles.pageTitle}>Truth Engine</h1>
          <span className={styles.volNum}>Vol. I</span>
        </div>
        <p className={styles.subtitle}>
          Submit any text for agentic claim extraction and evidence verification.
        </p>
      </div>

      {/* Input */}
      <div
        className={styles.inputBox}
      >
        <div className={styles.inputLabel}>
          <div className={styles.inputMark} />
          Statement for Verification
        </div>
        <textarea
          className={styles.textarea}
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Paste any article excerpt, claim, or statement to verify…"
          rows={6}
        />
        <div className={styles.charCount}>{text.length} characters</div>
      </div>

      {/* Sample chips */}
      <div className={styles.samples}>
        {SAMPLES.map((s, i) => (
          <button key={i} className={styles.sampleChip} onClick={() => setText(s)}>
            Sample {i + 1}
          </button>
        ))}
      </div>

      {/* Submit */}
      <Button
        onClick={runCheck}
        disabled={state === 'loading' || !text.trim()}
      >
        {state === 'loading' ? '⟳ Analysing…' : '⚡ Verify Claims'}
      </Button>

      {state === 'loading' && (
        <Suspense
          fallback={
            <p style={{ fontFamily: 'var(--f-mono)', fontSize: 12, color: 'var(--ink-muted)', marginTop: 16 }}>
              Preparing verification stream…
            </p>
          }
        >
          <SectionErrorBoundary fallbackText="Verification stream unavailable.">
            <TerminalStream lines={STREAM_LINES} />
          </SectionErrorBoundary>
        </Suspense>
      )}
      {state === 'error' && (
        <p style={{ fontFamily: 'var(--f-mono)', fontSize: 12, color: '#c8281e', marginTop: 16 }}>
          ■ {errorMessage || 'Verification failed — backend unavailable.'}
        </p>
      )}

      {/* Results */}
      {state === 'done' && results && (
        <div>
          <div className={styles.sectionDiv}>
            <div className={styles.sectionHeavy} />
            <div className={styles.sectionLabel}>
              <div className={styles.sectionMark} />
              {evaluations.length} Claims Evaluated
            </div>
            <div className={styles.sectionHeavy} />
          </div>

          <div className={styles.summary}>
            <div className={styles.countBadge} style={{ color: '#1a7a52', borderColor: '#1a7a52' }}>
              ■ {counts.supported} Supported
            </div>
            <div className={styles.countBadge} style={{ color: '#c8281e', borderColor: '#c8281e' }}>
              ■ {counts.contradicted} Contradicted
            </div>
            <div className={styles.countBadge} style={{ color: '#b5830a', borderColor: '#b5830a' }}>
              ■ {counts.unverified} Unverified
            </div>
          </div>

          <SectionErrorBoundary fallbackText="A claim card failed to render.">
            <Suspense
              fallback={
                <p style={{ fontFamily: 'var(--f-mono)', fontSize: 12, color: 'var(--ink-muted)', marginTop: 16 }}>
                  Loading claim cards…
                </p>
              }
            >
              {paginatedEvaluations.map((ev, i) => (
                <SectionErrorBoundary key={`${ev.claim}-${i}`} fallbackText={`Claim ${i + 1} unavailable.`}>
                  <ClaimCard evaluation={ev} index={i} />
                </SectionErrorBoundary>
              ))}
            </Suspense>
          </SectionErrorBoundary>

          {evaluations.length > PAGE_SIZE && (
            <div className={styles.samples} style={{ marginTop: 12 }}>
              <button
                className={styles.sampleChip}
                disabled={safePage === 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
              >
                Prev
              </button>
              <button className={styles.sampleChip} disabled>
                Page {safePage} / {totalPages}
              </button>
              <button
                className={styles.sampleChip}
                disabled={safePage === totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
