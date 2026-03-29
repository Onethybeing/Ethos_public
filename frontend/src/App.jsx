import { useEffect, useState } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { motion as Motion, AnimatePresence } from 'framer-motion'
import Navbar from './components/Navbar/Navbar'
import StatusBar from './components/StatusBar/StatusBar'
import Feed from './pages/Feed/Feed'
import TruthEngine from './pages/TruthEngine/TruthEngine'
import Constitution from './pages/Constitution/Constitution'
import Leaderboard from './pages/Leaderboard/Leaderboard'
import Auth from './pages/Auth/Auth'
import {
  clearAuthSession,
  getCurrentUser,
  getMe,
  hasAccessToken,
} from './api/client'
import styles from './App.module.css'

const pageVariants = {
  initial: { opacity: 0, y: 12 },
  enter: { opacity: 1, y: 0, transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.18, ease: 'easeIn' } },
}

export default function App() {
  const location = useLocation()
  const [booting, setBooting] = useState(true)
  const [user, setUser] = useState(null)
  const [showSignupSetup, setShowSignupSetup] = useState(false)
  const readerLabel = user?.display_name || user?.username || user?.id || 'anonymous'

  useEffect(() => {
    let isMounted = true

    async function bootstrap() {
      if (!hasAccessToken()) {
        if (isMounted) {
          setUser(null)
          setShowSignupSetup(false)
          setBooting(false)
        }
        return
      }

      const cachedUser = getCurrentUser()
      if (isMounted && cachedUser) {
        setUser(cachedUser)
      }

      try {
        const me = await getMe()
        if (!isMounted) return
        setUser(me)
        setShowSignupSetup(false)
      } catch {
        clearAuthSession()
        if (!isMounted) return
        setUser(null)
        setShowSignupSetup(false)
      } finally {
        if (isMounted) setBooting(false)
      }
    }

    bootstrap()
    return () => { isMounted = false }
  }, [])

  async function handleAuthSuccess(authUser, source) {
    setUser(authUser)
    setShowSignupSetup(source === 'signup' && !authUser?.onboarding_completed)
  }

  async function handleOnboardingComplete() {
    try {
      const me = await getMe()
      setUser(me)
      setShowSignupSetup(false)
    } catch {
      setShowSignupSetup(false)
    }
  }

  function handleSkipSignupSetup() {
    setShowSignupSetup(false)
  }

  function handleLogout() {
    clearAuthSession()
    setUser(null)
    setShowSignupSetup(false)
  }

  if (booting) {
    return (
      <div className={styles.centerScreen}>
        <div className={styles.centerCard}>Loading session…</div>
      </div>
    )
  }

  if (!user) {
    return <Auth onSuccess={handleAuthSuccess} />
  }

  if (showSignupSetup) {
    return (
      <div className={styles.fullscreenSetup}>
        <Constitution
          onboardingMode
          fullScreenMode
          onSkipOnboarding={handleSkipSignupSetup}
          onOnboardingComplete={handleOnboardingComplete}
        />
      </div>
    )
  }

  return (
    <div className={styles.app}>
      <Navbar currentUserId={readerLabel} currentUser={user} onLogout={handleLogout} />
      <main className={styles.main}>
        <AnimatePresence mode="wait" initial={false}>
          <Motion.div
            key={location.pathname}
            variants={pageVariants}
            initial="initial"
            animate="enter"
            exit="exit"
            style={{ flex: 1 }}
          >
            <Routes location={location}>
              <Route path="/" element={<Feed />} />
              <Route path="/feed" element={<Feed />} />
              <Route path="/truth-engine" element={<TruthEngine />} />
              <Route path="/constitution" element={<Constitution />} />
              <Route path="/leaderboard" element={<Leaderboard currentUserId={user.id} />} />
            </Routes>
          </Motion.div>
        </AnimatePresence>
      </main>
      <StatusBar currentUserId={readerLabel} />
    </div>
  )
}
