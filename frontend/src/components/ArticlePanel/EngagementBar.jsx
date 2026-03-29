import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowBigUp, ArrowBigDown, Lock } from 'lucide-react';
import { getEngagementStatus, voteArticle } from '../../api/client';
import styles from './EngagementBar.module.css';

export default function EngagementBar({ articleId, hasRead: initialHasRead }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isCasting, setIsCasting] = useState(false);

    useEffect(() => {
        loadStatus();
    }, [articleId]);

    async function loadStatus() {
        try {
            const status = await getEngagementStatus(articleId);
            setData(status);
        } catch (err) {
            console.error('Failed to load engagement status', err);
        } finally {
            setLoading(false);
        }
    }

    async function handleVote(voteType) {
        if (isCasting) return;

        // Determine new vote value: toggling same vote clears it (0)
        const oldVote = data?.current_vote;
        const newVote = oldVote === voteType ? 0 : voteType;

        // --- OPTIMISTIC UPDATE ---
        // We update the local data immediately so the user sees results at 0ms
        setData(prev => {
            if (!prev) return prev;
            let newUp = prev.vote_count_up;
            let newDown = prev.vote_count_down;

            // Subtract old vote effect
            if (oldVote === 1) newUp--;
            if (oldVote === -1) newDown--;

            // Add new vote effect
            if (newVote === 1) newUp++;
            if (newVote === -1) newDown++;

            return {
                ...prev,
                current_vote: newVote,
                vote_count_up: newUp,
                vote_count_down: newDown
            };
        });

        setIsCasting(true);
        try {
            await voteArticle(articleId, newVote);
            // Optional: sync with actual server state if needed 
            // (but optimistic update already handled the "look")
        } catch (err) {
            // ROLLBACK on error
            console.error('Voting failed, rolling back.', err);
            loadStatus();
            alert(err.response?.data?.detail || 'Voting failed');
        } finally {
            setIsCasting(false);
        }
    }

    if (loading) return <div className={styles.skeleton} />;

    const { current_vote, vote_count_up, vote_count_down } = data || {};

    return (
        <div className={styles.bar}>
            <div className={styles.votes}>
                <button
                    className={`${styles.voteBtn} ${current_vote === 1 ? styles.upvoted : ''}`}
                    onClick={() => handleVote(1)}
                    title="Upvote"
                >
                    <ArrowBigUp fill={current_vote === 1 ? "currentColor" : "none"} size={22} />
                    <span className={styles.count}>{vote_count_up}</span>
                </button>

                <button
                    className={`${styles.voteBtn} ${current_vote === -1 ? styles.downvoted : ''}`}
                    onClick={() => handleVote(-1)}
                    title="Downvote"
                >
                    <ArrowBigDown fill={current_vote === -1 ? "currentColor" : "none"} size={22} />
                    <span className={styles.count}>{vote_count_down}</span>
                </button>
            </div>
        </div>
    );
}
