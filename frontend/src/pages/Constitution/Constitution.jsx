import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Button from '../../components/ui/Button'
import { generatePNC, getPNC, savePNC, USER_ID } from '../../api/client'
import styles from './Constitution.module.css'

const TOTAL_STEPS = 4

const MODES = [
  { id: 'empiricist',  icon: '🔬', name: 'Empiricist',  desc: 'Prioritise peer-reviewed evidence, primary sources, and quantifiable claims.' },
  { id: 'rationalist', icon: '🧠', name: 'Rationalist', desc: 'Favour logical consistency, first-principles reasoning, and systematic analysis.' },
  { id: 'narrative',   icon: '📖', name: 'Narrative',   desc: 'Value contextual storytelling, lived experience, and qualitative framing.' },
]

function ArcMeter({ value, color = 'var(--red)', size = 54 }) {
  const r = 20
  const circ = 2 * Math.PI * r
  return (
    <svg width={size} height={size} viewBox="0 0 54 54">
      <circle cx="27" cy="27" r={r} fill="none" stroke="var(--rule-light)" strokeWidth="4" />
      <motion.circle
        cx="27" cy="27" r={r}
        fill="none" stroke={color} strokeWidth="4"
        strokeDasharray={circ}
        initial={{ strokeDashoffset: circ }}
        animate={{ strokeDashoffset: circ - value * circ }}
        transition={{ duration: 0.9, ease: [0.34, 1.1, 0.64, 1] }}
        strokeLinecap="square"
        transform="rotate(-90 27 27)"
      />
      <text x="27" y="27" textAnchor="middle" dominantBaseline="central"
        fill={color} fontSize="9" fontFamily="IBM Plex Mono" fontWeight="700">
        {Math.round(value * 100)}%
      </text>
    </svg>
  )
}

export default function Constitution() {
  const [step,    setStep]    = useState(0)
  const [loading, setLoading] = useState(false)
  const [saved,   setSaved]   = useState(false)
  const [pnc,     setPnc]     = useState(null)

  const [form, setForm] = useState({
    nl: '',
    mode: 'empiricist',
    vThresh: 0.78,
    divWeight: 0.65,
    biasT: 'low',
    depth: 'expert',
    density: 'high',
    priorities: ['technology', 'AI', 'science'],
    excluded: ['celebrity gossip', 'sports'],
  })
  const [pTag, setPTag] = useState('')
  const [eTag, setETag] = useState('')

  useEffect(() => {
    getPNC().then(d => { if (d) setPnc(d) })
  }, [])

  async function generate() {
    setLoading(true)
    const d = await generatePNC(form.nl)
    setPnc(d || {
      user_id: USER_ID,
      epistemic_framework:    { primary_mode: form.mode, verification_threshold: form.vThresh },
      narrative_preferences:  { diversity_weight: form.divWeight, bias_tolerance: form.biasT },
      topical_constraints:    { priority_domains: [...form.priorities], excluded_topics: [...form.excluded] },
      complexity_preference:  { readability_depth: form.depth, data_density: form.density },
    })
    setLoading(false)
    setStep(TOTAL_STEPS)
  }

  async function handleSave() {
    if (!pnc) return
    await savePNC(pnc)
    setSaved(true)
    setTimeout(() => setSaved(false), 2200)
  }

  function addTag(type) {
    if (type === 'p' && pTag.trim()) {
      setForm(f => ({ ...f, priorities: [...f.priorities, pTag.trim()] }))
      setPTag('')
    }
    if (type === 'e' && eTag.trim()) {
      setForm(f => ({ ...f, excluded: [...f.excluded, eTag.trim()] }))
      setETag('')
    }
  }

  const progressPct = (step / TOTAL_STEPS) * 100

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--red)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 }}>
          ■ Personal News Constitution
        </div>
        <h1 className={styles.pageTitle}>Your Constitution</h1>
        <p className={styles.subtitle}>
          Define your epistemic relationship with information.
        </p>
      </div>

      {/* Progress */}
      {step < TOTAL_STEPS && (
        <div className={styles.progressWrap}>
          <div className={styles.progressTrack}>
            <motion.div
              className={styles.progressFill}
              animate={{ width: `${progressPct}%` }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            />
          </div>
          <div className={styles.progressLabel}>
            <span>§ {step + 1} / {TOTAL_STEPS}</span>
            <span>{['Statement', 'Mode', 'Thresholds', 'Domains'][step]}</span>
          </div>
        </div>
      )}

      <AnimatePresence mode="wait">
        {/* Step 0 */}
        {step === 0 && (
          <motion.div key="s0"
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}>
            <div className={styles.stepSection}>§ 1 / 4 · Statement of Intent</div>
            <h2 className={styles.stepTitle}>Describe your ideal news diet</h2>
            <p className={styles.stepDesc}>What topics matter to you? What level of evidence do you demand? What should be filtered?</p>
            <textarea className={styles.textarea} rows={5} value={form.nl}
              onChange={e => setForm(f => ({ ...f, nl: e.target.value }))}
              placeholder="I want rigorous tech and AI coverage with high verification standards. No clickbait. I care deeply about science, climate policy, and CRISPR breakthroughs…" />
            <div className={styles.stepNav}>
              <Button onClick={() => setStep(1)} disabled={!form.nl.trim()}>Continue →</Button>
            </div>
          </motion.div>
        )}

        {/* Step 1 */}
        {step === 1 && (
          <motion.div key="s1"
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}>
            <div className={styles.stepSection}>§ 2 / 4 · Editorial Stance</div>
            <h2 className={styles.stepTitle}>Choose your epistemic mode</h2>
            <p className={styles.stepDesc}>How do you evaluate claims? This shapes how the algorithm weights sources and narrative framing.</p>
            <div className={styles.modeTiles}>
              {MODES.map(m => (
                <button key={m.id} className={`${styles.modeTile} ${form.mode === m.id ? styles.selected : ''}`}
                  onClick={() => setForm(f => ({ ...f, mode: m.id }))}>
                  <span className={styles.modeIcon}>{m.icon}</span>
                  <span className={styles.modeName}>{m.name}</span>
                  <span className={styles.modeDesc}>{m.desc}</span>
                </button>
              ))}
            </div>
            <div className={styles.stepNav}>
              <Button variant="secondary" onClick={() => setStep(0)}>← Back</Button>
              <Button onClick={() => setStep(2)}>Continue →</Button>
            </div>
          </motion.div>
        )}

        {/* Step 2 */}
        {step === 2 && (
          <motion.div key="s2"
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}>
            <div className={styles.stepSection}>§ 3 / 4 · Calibration</div>
            <h2 className={styles.stepTitle}>Set your thresholds</h2>
            <p className={styles.stepDesc}>How strictly do you want claims verified? How much do you value diverse narrative perspectives?</p>
            <div className={styles.sliderGroup}>
              <div className={styles.sliderHead}>
                <span>Verification Threshold</span>
                <span className={styles.sliderVal}>{Math.round(form.vThresh * 100)}%</span>
              </div>
              <input type="range" className={styles.slider} min="0" max="1" step="0.01"
                value={form.vThresh} onChange={e => setForm(f => ({ ...f, vThresh: +e.target.value }))} />
            </div>
            <div className={styles.sliderGroup}>
              <div className={styles.sliderHead}>
                <span>Diversity Weight</span>
                <span className={styles.sliderVal}>{Math.round(form.divWeight * 100)}%</span>
              </div>
              <input type="range" className={styles.slider} min="0" max="1" step="0.01"
                value={form.divWeight} onChange={e => setForm(f => ({ ...f, divWeight: +e.target.value }))} />
            </div>
            <div className={styles.stepNav}>
              <Button variant="secondary" onClick={() => setStep(1)}>← Back</Button>
              <Button onClick={() => setStep(3)}>Continue →</Button>
            </div>
          </motion.div>
        )}

        {/* Step 3 */}
        {step === 3 && (
          <motion.div key="s3"
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}>
            <div className={styles.stepSection}>§ 4 / 4 · Topical Domains</div>
            <h2 className={styles.stepTitle}>Define your boundaries</h2>
            <p className={styles.stepDesc}>What topics should the feed prioritise? What should be excluded entirely?</p>

            <div className={styles.tagGroup}>
              <label className={styles.tagLabel}>Priority Domains</label>
              <div className={styles.tagList}>
                {form.priorities.map(t => (
                  <span key={t} className={`${styles.tag} ${styles.priority}`}>
                    {t}
                    <button className={styles.tagRemove} onClick={() => setForm(f => ({ ...f, priorities: f.priorities.filter(x => x !== t) }))}>×</button>
                  </span>
                ))}
              </div>
              <div className={styles.tagInputRow}>
                <input className={styles.tagInput} value={pTag} onChange={e => setPTag(e.target.value)}
                  placeholder="add topic…" onKeyDown={e => e.key === 'Enter' && addTag('p')} />
                <Button variant="secondary" onClick={() => addTag('p')}>+ Add</Button>
              </div>
            </div>

            <div className={styles.tagGroup}>
              <label className={styles.tagLabel}>Excluded Topics</label>
              <div className={styles.tagList}>
                {form.excluded.map(t => (
                  <span key={t} className={`${styles.tag} ${styles.excluded}`}>
                    {t}
                    <button className={styles.tagRemove} onClick={() => setForm(f => ({ ...f, excluded: f.excluded.filter(x => x !== t) }))}>×</button>
                  </span>
                ))}
              </div>
              <div className={styles.tagInputRow}>
                <input className={styles.tagInput} value={eTag} onChange={e => setETag(e.target.value)}
                  placeholder="add exclusion…" onKeyDown={e => e.key === 'Enter' && addTag('e')} />
                <Button variant="secondary" onClick={() => addTag('e')}>+ Add</Button>
              </div>
            </div>

            <div className={styles.stepNav}>
              <Button variant="secondary" onClick={() => setStep(2)}>← Back</Button>
              <Button onClick={generate} disabled={loading}>
                {loading ? '⟳ Generating…' : '⚡ Generate Constitution'}
              </Button>
            </div>
          </motion.div>
        )}

        {/* Result */}
        {step === TOTAL_STEPS && pnc && (
          <motion.div key="result"
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}>
            <div className={styles.constitutionCard}>
              <div className={styles.constHead}>
                <span className={styles.constTitle}>Constitution of {pnc.user_id}</span>
                <span className={styles.constDate}>{new Date().toISOString().split('T')[0]}</span>
              </div>
              <div className={styles.constGrid}>
                <div className={styles.constField}>
                  <div className={styles.constFieldLabel}>Epistemic Mode</div>
                  <span className={styles.modeBadge}>{pnc.epistemic_framework.primary_mode}</span>
                </div>
                <div className={styles.constField}>
                  <div className={styles.constFieldLabel}>Bias Tolerance · Complexity</div>
                  <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginTop: 4 }}>
                    {[pnc.narrative_preferences.bias_tolerance, pnc.complexity_preference.readability_depth].map(t => (
                      <span key={t} style={{ fontFamily: 'var(--f-mono)', fontSize: 10, padding: '2px 7px', border: '1px solid var(--rule)', color: 'var(--ink-muted)' }}>{t}</span>
                    ))}
                  </div>
                </div>
                <div className={styles.constField}>
                  <div className={styles.constFieldLabel}>Verification Threshold</div>
                  <div className={styles.arcWrap}>
                    <ArcMeter value={pnc.epistemic_framework.verification_threshold} color="var(--red)" />
                    <span className={styles.arcVal}>{Math.round(pnc.epistemic_framework.verification_threshold * 100)}%</span>
                  </div>
                </div>
                <div className={styles.constField}>
                  <div className={styles.constFieldLabel}>Diversity Weight</div>
                  <div className={styles.arcWrap}>
                    <ArcMeter value={pnc.narrative_preferences.diversity_weight} color="#2a4a8a" />
                    <span className={styles.arcVal}>{Math.round(pnc.narrative_preferences.diversity_weight * 100)}%</span>
                  </div>
                </div>
                <div className={`${styles.constField} ${styles.wide}`}>
                  <div className={styles.constFieldLabel}>Priority Domains</div>
                  <div className={styles.tagList} style={{ marginTop: 5 }}>
                    {pnc.topical_constraints.priority_domains.map(t => (
                      <span key={t} className={`${styles.tag} ${styles.priority}`}>{t}</span>
                    ))}
                  </div>
                </div>
                <div className={`${styles.constField} ${styles.wide}`}>
                  <div className={styles.constFieldLabel}>Excluded Topics</div>
                  <div className={styles.tagList} style={{ marginTop: 5 }}>
                    {pnc.topical_constraints.excluded_topics.map(t => (
                      <span key={t} className={`${styles.tag} ${styles.excluded}`}>{t}</span>
                    ))}
                  </div>
                </div>
              </div>
              <motion.button
                className={`${styles.constSaveBtn} ${saved ? styles.saved : ''}`}
                onClick={handleSave}
                whileTap={{ scale: 0.98 }}
              >
                {saved ? '✓ Saved to Server' : '↑ Save Constitution'}
              </motion.button>
            </div>
            <div className={styles.stepNav} style={{ marginTop: 16 }}>
              <Button variant="secondary" onClick={() => setStep(0)}>↺ Rebuild</Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
