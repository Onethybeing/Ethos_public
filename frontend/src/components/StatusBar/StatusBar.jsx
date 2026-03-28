import { useState, useEffect } from 'react'
import { USER_ID } from '../../api/client'
import styles from './StatusBar.module.css'

export default function StatusBar() {
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className={styles.bar}>
      <div className={`${styles.item} ${styles.ok}`}>
        <div className={styles.dot} style={{ background: 'currentColor' }} />
        API CONNECTED
      </div>
      <div className={`${styles.item} ${styles.ok}`}>
        <div className={styles.dot} style={{ background: 'currentColor' }} />
        GDELT LIVE
      </div>
      <div className={styles.item}>
        USER · {USER_ID}
      </div>
      <div className={`${styles.item} ${styles.right}`}>
        ETHOSNEWS v1.0 · {time.toLocaleTimeString('en-GB', { hour12: false })}
      </div>
    </div>
  )
}
