import { motion } from 'framer-motion'
import styles from './TerminalStream.module.css'

export default function TerminalStream({ lines = [] }) {
  const ts = new Date().toLocaleTimeString('en-GB', { hour12: false })
  return (
    <div className={styles.terminal}>
      {lines.map((line, i) => (
        <motion.div
          key={i}
          className={styles.line}
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.22, duration: 0.28, ease: 'easeOut' }}
        >
          <span className={styles.ts}>[{ts}]</span>
          <span className={styles.text}>{line}</span>
        </motion.div>
      ))}
      <motion.div
        className={styles.line}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: lines.length * 0.22 }}
      >
        <span className={styles.ts}>[{ts}]</span>
        <span className={styles.cursor}>▌</span>
      </motion.div>
    </div>
  )
}
