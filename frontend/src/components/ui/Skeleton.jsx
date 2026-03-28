import styles from './Skeleton.module.css'

export function SkeletonCard() {
  return (
    <div className={styles.card}>
      <div className={`${styles.line} ${styles.short} skeleton-base`} />
      <div className={`${styles.line} ${styles.title} skeleton-base`} />
      <div className={`${styles.line} ${styles.title} ${styles.titleShort} skeleton-base`} />
      <div className={`${styles.line} ${styles.meta} skeleton-base`} />
      <div className={`${styles.line} ${styles.body} skeleton-base`} />
      <div className={`${styles.line} ${styles.body} skeleton-base`} />
      <div className={`${styles.line} ${styles.bodyShort} skeleton-base`} />
    </div>
  )
}

export function SkeletonRow() {
  return (
    <div className={styles.row}>
      <div className={`${styles.rankBlock} skeleton-base`} />
      <div className={styles.rowContent}>
        <div className={`${styles.line} ${styles.meta} skeleton-base`} />
        <div className={`${styles.line} ${styles.bar} skeleton-base`} />
      </div>
      <div className={`${styles.scoreBlock} skeleton-base`} />
    </div>
  )
}
