import { useState } from 'react'
import { motion } from 'framer-motion'
import ClaimCard from '../../components/ClaimCard/ClaimCard'
import TerminalStream from '../../components/ui/TerminalStream'
import Button from '../../components/ui/Button'
import { factCheckText } from '../../api/client'
import styles from './TruthEngine.module.css'

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

  async function runCheck() {
    if (!text.trim()) return
    setState('loading')
    setResults(null)
    const data = await factCheckText(text)
    setResults(data)
    setState('done')
  }

  const counts = results ? {
    supported:    results.evaluations.filter(e => e.verdict === 'supported').length,
    contradicted: results.evaluations.filter(e => e.verdict === 'contradicted').length,
    unverified:   results.evaluations.filter(e => ['unverified','not-mentioned'].includes(e.verdict)).length,
  } : null

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
      <motion.div
        className={styles.inputBox}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
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
      </motion.div>

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

      {state === 'loading' && <TerminalStream lines={STREAM_LINES} />}

      {/* Results */}
      {state === 'done' && results && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          <div className={styles.sectionDiv}>
            <div className={styles.sectionHeavy} />
            <div className={styles.sectionLabel}>
              <div className={styles.sectionMark} />
              {results.evaluations.length} Claims Evaluated
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

          {results.evaluations.map((ev, i) => (
            <ClaimCard key={i} evaluation={ev} index={i} />
          ))}
        </motion.div>
      )}
    </div>
  )
}
