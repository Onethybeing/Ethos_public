import { useMemo, useState } from 'react'
import Button from '../../components/ui/Button'
import { login, signup } from '../../api/client'
import styles from './Auth.module.css'

export default function Auth({ onSuccess }) {
  const [mode, setMode] = useState('login')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    identity: '',
    username: '',
    email: '',
    display_name: '',
    password: '',
  })

  const title = useMemo(() => (
    mode === 'login' ? 'Sign in to EthosNews' : 'Create your EthosNews account'
  ), [mode])

  function updateField(key, value) {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (mode === 'login') {
        const data = await login({
          identity: form.identity.trim(),
          password: form.password,
        })
        onSuccess(data.user, 'login')
      } else {
        const data = await signup({
          username: form.username.trim(),
          email: form.email.trim() || null,
          display_name: form.display_name.trim() || null,
          password: form.password,
        })
        onSuccess(data.user, 'signup')
      }
    } catch (err) {
      const message = err?.response?.data?.detail
      setError(typeof message === 'string' ? message : 'Authentication failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <div className={styles.kicker}>■ EthosNews Access</div>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.subtitle}>
          {mode === 'login'
            ? 'Use your username or email and continue to your feed.'
            : 'Create your account and set up your personal news constitution.'}
        </p>

        {mode === 'signup' && (
          <>
            <label className={styles.label} htmlFor="username">Username</label>
            <input
              id="username"
              className={styles.input}
              value={form.username}
              onChange={(e) => updateField('username', e.target.value)}
              required
            />

            <label className={styles.label} htmlFor="display_name">Display Name (optional)</label>
            <input
              id="display_name"
              className={styles.input}
              value={form.display_name}
              onChange={(e) => updateField('display_name', e.target.value)}
            />

            <label className={styles.label} htmlFor="email">Email (optional)</label>
            <input
              id="email"
              className={styles.input}
              value={form.email}
              onChange={(e) => updateField('email', e.target.value)}
              type="email"
            />
          </>
        )}

        {mode === 'login' && (
          <>
            <label className={styles.label} htmlFor="identity">Username or Email</label>
            <input
              id="identity"
              className={styles.input}
              value={form.identity}
              onChange={(e) => updateField('identity', e.target.value)}
              required
            />
          </>
        )}

        <label className={styles.label} htmlFor="password">Password</label>
        <input
          id="password"
          className={styles.input}
          value={form.password}
          onChange={(e) => updateField('password', e.target.value)}
          type="password"
          required
          minLength={8}
        />

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.actions}>
          <Button type="submit" disabled={loading}>
            {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Sign Up'}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setError('')
              setMode(prev => (prev === 'login' ? 'signup' : 'login'))
            }}
          >
            {mode === 'login' ? 'Create account' : 'I already have an account'}
          </Button>
        </div>
      </form>
    </div>
  )
}
