import { useState, useEffect, useRef } from 'react'
import { AnimatePresence } from 'framer-motion'
import FeedCard from '../../components/FeedCard/FeedCard'
import ArticlePanel from '../../components/ArticlePanel/ArticlePanel'
import { SkeletonCard } from '../../components/ui/Skeleton'
import { getFeed, getPersonalizedFeed, getArticle } from '../../api/client'
import styles from './Feed.module.css'

const CATEGORIES = ['All', 'Technology', 'Finance', 'Science', 'Politics', 'Health', 'Policy']

export default function Feed() {
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(true)
  const [personalized, setPersonalized] = useState(false)
  const [filter, setFilter] = useState('All')
  const [trending, setTrending] = useState(false)
  const [selected, setSelected] = useState(null)
  const prefetchedArticlesRef = useRef(new Map())
  const prefetchInFlightRef = useRef(new Map())

  useEffect(() => {
    const fetchPromise = personalized ? getPersonalizedFeed() : getFeed(filter, trending)
    fetchPromise
      .then(data => setArticles(data || []))
      .catch(() => setArticles([]))
      .finally(() => setLoading(false))
  }, [personalized, filter, trending])

  const filtered = personalized
    ? (filter === 'All' ? articles : articles.filter(a => a.category === filter))
    : articles

  function getHydratedArticle(article) {
    const prefetched = prefetchedArticlesRef.current.get(article.id)
    return prefetched ? { ...article, ...prefetched } : article
  }

  function prefetchArticle(articleId) {
    if (!articleId) return
    if (prefetchedArticlesRef.current.has(articleId) || prefetchInFlightRef.current.has(articleId)) return

    const request = getArticle(articleId)
      .then((full) => {
        if (!full) return
        prefetchedArticlesRef.current.set(articleId, full)

        setArticles(prev => prev.map(item => (item.id === articleId ? { ...item, ...full } : item)))
        setSelected(prev => (prev && prev.id === articleId ? { ...prev, ...full } : prev))
      })
      .catch(() => {
        // Prefetch is opportunistic; failures should not block normal click behavior.
      })
      .finally(() => {
        prefetchInFlightRef.current.delete(articleId)
      })

    prefetchInFlightRef.current.set(articleId, request)
  }

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
            onClick={() => {
              setLoading(true)
              setFilter(cat)
            }}
          >
            {cat}
          </button>
        ))}

        <div className={styles.toggleGroup}>
          <div className={styles.toggleWrap} onClick={() => {
            setLoading(true)
            setTrending(t => !t)
          }}>
            <div className={`${styles.toggle} ${trending ? styles.on : ''}`}>
              <div className={styles.toggleThumb} />
            </div>
            Trending
          </div>

          <div className={styles.toggleWrap} onClick={() => {
            setLoading(true)
            setPersonalized(p => !p)
          }}>
            <div className={`${styles.toggle} ${personalized ? styles.on : ''}`}>
              <div className={styles.toggleThumb} />
            </div>
            Personalised
          </div>
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
                onHover={() => prefetchArticle(article.id)}
                onClick={() => {
                  prefetchArticle(article.id)
                  setSelected(getHydratedArticle(article))
                }}
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
