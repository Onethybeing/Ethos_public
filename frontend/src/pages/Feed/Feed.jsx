import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import FeedCard from '../../components/FeedCard/FeedCard'
import ArticlePanel from '../../components/ArticlePanel/ArticlePanel'
import { SkeletonCard } from '../../components/ui/Skeleton'
import { getFeed, getPersonalizedFeed } from '../../api/client'
import styles from './Feed.module.css'

const CATEGORIES = ['All', 'Technology', 'Finance', 'Science', 'Politics', 'Health', 'Policy']

export default function Feed() {
  const [articles,     setArticles]     = useState([])
  const [loading,      setLoading]      = useState(true)
  const [personalized, setPersonalized] = useState(false)
  const [filter,       setFilter]       = useState('All')
  const [selected,     setSelected]     = useState(null)

  useEffect(() => {
    setLoading(true)
    const fetch = personalized ? getPersonalizedFeed : getFeed
    fetch().then(data => {
      setArticles(data || [])
      setLoading(false)
    })
  }, [personalized])

  const filtered = filter === 'All'
    ? articles
    : articles.filter(a => a.category === filter)

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerTop}>
          <h1 className={styles.pageTitle}>Intelligence Feed</h1>
          <span className={styles.articleCount}>
            {loading ? '—' : `${filtered.length} articles`}
          </span>
        </div>
        <div className={styles.rule3} />
        <div className={styles.rule1} />
      </div>

      {/* Toolbar */}
      <div className={styles.toolbar}>
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            className={`${styles.filterBtn} ${filter === cat ? styles.active : ''}`}
            onClick={() => setFilter(cat)}
          >
            {cat}
          </button>
        ))}

        <div className={styles.toggleWrap} onClick={() => setPersonalized(p => !p)}>
          <div className={`${styles.toggle} ${personalized ? styles.on : ''}`}>
            <div className={styles.toggleThumb} />
          </div>
          Personalised
        </div>
      </div>

      {/* Masonry */}
      <div className={styles.masonry}>
        {loading
          ? [...Array(6)].map((_, i) => <SkeletonCard key={i} />)
          : filtered.length === 0
            ? (
              <div className={styles.empty}>
                <div className={styles.emptyLabel}>No articles match this filter</div>
              </div>
            )
            : filtered.map((article, i) => (
              <FeedCard
                key={article.id}
                article={article}
                index={i}
                featured={i === 0 && filter === 'All'}
                onClick={() => setSelected(article)}
              />
            ))
        }
      </div>

      {/* Article Panel overlay */}
      <AnimatePresence>
        {selected && (
          <ArticlePanel
            article={selected}
            onClose={() => setSelected(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
