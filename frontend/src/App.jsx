import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import Navbar from './components/Navbar/Navbar'
import StatusBar from './components/StatusBar/StatusBar'
import Feed from './pages/Feed/Feed'
import TruthEngine from './pages/TruthEngine/TruthEngine'
import Constitution from './pages/Constitution/Constitution'
import Leaderboard from './pages/Leaderboard/Leaderboard'
import styles from './App.module.css'

const pageVariants = {
  initial: { opacity: 0, y: 12 },
  enter:   { opacity: 1, y: 0, transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] } },
  exit:    { opacity: 0, y: -8, transition: { duration: 0.18, ease: 'easeIn' } },
}

export default function App() {
  const location = useLocation()
  return (
    <div className={styles.app}>
      <Navbar />
      <main className={styles.main}>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={location.pathname}
            variants={pageVariants}
            initial="initial"
            animate="enter"
            exit="exit"
            style={{ flex: 1 }}
          >
            <Routes location={location}>
              <Route path="/"              element={<Feed />} />
              <Route path="/feed"          element={<Feed />} />
              <Route path="/truth-engine"  element={<TruthEngine />} />
              <Route path="/constitution"  element={<Constitution />} />
              <Route path="/leaderboard"   element={<Leaderboard />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </main>
      <StatusBar />
    </div>
  )
}
