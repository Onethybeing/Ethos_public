import { useEffect, useState } from 'react'
import Button from '../../components/ui/Button'
import { getOnboardingQuestions, submitOnboarding } from '../../api/client'
import styles from './Onboarding.module.css'

export default function Onboarding({ onComplete, onLogout }) {
  const [questions, setQuestions] = useState([])
  const [answers, setAnswers] = useState({})
  const [loadingQuestions, setLoadingQuestions] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true

    getOnboardingQuestions()
      .then((data) => {
        if (!mounted) return
        const list = data?.questions || []
        setQuestions(list)

        const initialAnswers = {}
        list.forEach((q) => { initialAnswers[q.id] = '' })
        setAnswers(initialAnswers)
      })
      .catch(() => {
        if (mounted) {
          setError('Failed to load onboarding questions.')
        }
      })
      .finally(() => {
        if (mounted) {
          setLoadingQuestions(false)
        }
      })

    return () => { mounted = false }
  }, [])

  function updateAnswer(id, value) {
    setAnswers(prev => ({ ...prev, [id]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    const missing = questions
      .filter(q => q.required)
      .filter(q => !String(answers[q.id] || '').trim())

    if (missing.length > 0) {
      setError(`Please answer all required questions before continuing.`)
      return
    }

    setSubmitting(true)
    try {
      await submitOnboarding(answers)
      onComplete()
    } catch (err) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to submit onboarding.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loadingQuestions) {
    return (
      <div className={styles.page}>
        <div className={styles.card}>Loading onboarding…</div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <div className={styles.kicker}>■ First-time setup</div>
        <h1 className={styles.title}>Set your Personal News Constitution</h1>
        <p className={styles.subtitle}>
          Answer in your own words. We’ll map everything to your structured preferences in one step.
        </p>

        {questions.map((question, idx) => (
          <div className={styles.questionBlock} key={question.id}>
            <label className={styles.label} htmlFor={question.id}>
              {idx + 1}. {question.question}
            </label>
            <div className={styles.helper}>{question.helper_text}</div>
            <textarea
              id={question.id}
              className={styles.textarea}
              rows={3}
              value={answers[question.id] || ''}
              onChange={(e) => updateAnswer(question.id, e.target.value)}
              required={question.required}
            />
          </div>
        ))}

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.actions}>
          <Button type="submit" disabled={submitting}>
            {submitting ? 'Submitting…' : 'Finish onboarding'}
          </Button>
          <Button type="button" variant="secondary" onClick={onLogout}>
            Sign out
          </Button>
        </div>
      </form>
    </div>
  )
}
