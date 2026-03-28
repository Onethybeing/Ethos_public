import { useEffect, useState, useRef } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { motion, useScroll, useTransform, AnimatePresence } from 'framer-motion'
import { USER_ID } from '../../api/client'
import styles from './Navbar.module.css'

const TABS = [
  { path: '/',             label: 'Intelligence Feed' },
  { path: '/truth-engine', label: 'Truth Engine' },
  { path: '/constitution', label: 'Constitution' },
  { path: '/leaderboard',  label: 'The Arena' },
]

export default function Navbar() {
  const navigate = useNavigate()
  const [scrolled, setScrolled] = useState(false)
  const [now, setNow] = useState(new Date())
  const { scrollY } = useScroll()

  // Compress masthead height on scroll
  const mastheadPaddingY = useTransform(scrollY, [0, 60], [14, 4])
  const mastheadFontSize = useTransform(scrollY, [0, 60], [1, 0.82])

  useEffect(() => {
    const tick = setInterval(() => setNow(new Date()), 60000)
    return () => clearInterval(tick)
  }, [])

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const dateStr = now.toLocaleDateString('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  }).toUpperCase()

  return (
    <motion.nav
      className={`${styles.navbar} ${scrolled ? styles.scrolled : ''}`}
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Row 1 — Meta */}
      <div className={styles.metaBar}>
        <span className={styles.metaDate}>{dateStr}</span>
        <span className={styles.liveBadge}>
          <span className={styles.liveDot} />
          GDELT · LIVE
          <span className={styles.liveDot} />
        </span>
        <span className={styles.metaUser}>
          READER: <span>{USER_ID}</span>
        </span>
      </div>

      {/* Rule 3px */}
      <div className={styles.rule3} />

      {/* Row 2 — Masthead */}
      <motion.div
        className={styles.masthead}
        style={{ paddingTop: mastheadPaddingY, paddingBottom: mastheadPaddingY }}
      >
        <motion.div
          className={styles.mastheadTitle}
          style={{ scale: mastheadFontSize }}
          style={{ transformOrigin: 'left center' }}
          onClick={() => navigate('/')}
        >
          The EthosNews
        </motion.div>

        <div className={styles.mastheadTagline}>
          Intelligence · Integrity · Inquiry
        </div>

        <div className={styles.mastheadMeta}>
          <div>Vol. I · No. 1</div>
          <div>Est. 2025</div>
          <div>Free Edition</div>
        </div>
      </motion.div>

      {/* Rule 1px */}
      <div className={styles.rule1} />

      {/* Row 3 — Tabs */}
      <div className={styles.navTabs}>
        {TABS.map((tab) => (
          <NavLink
            key={tab.path}
            to={tab.path}
            end={tab.path === '/'}
            className={({ isActive }) =>
              `${styles.navTab} ${isActive ? styles.active : ''}`
            }
          >
            {({ isActive }) => (
              <>
                {tab.label}
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className={styles.tabIndicator}
                    style={{ left: 0, right: 0 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 40 }}
                  />
                )}
              </>
            )}
          </NavLink>
        ))}
      </div>
    </motion.nav>
  )
}
