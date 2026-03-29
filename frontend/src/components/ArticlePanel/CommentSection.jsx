import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, MessageSquare, CornerDownRight, Trash2 } from 'lucide-react';
import { getComments, postComment, getCurrentUserId } from '../../api/client';
import { formatDate } from '../../utils/helpers';
import Button from '../ui/Button';
import styles from './CommentSection.module.css';

export default function CommentSection({ articleId }) {
    const [comments, setComments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [newComment, setNewComment] = useState('');
    const [replyTo, setReplyTo] = useState(null); // { id, username }
    const [isSubmitting, setIsSubmitting] = useState(false);
    const currentUserId = getCurrentUserId();

    useEffect(() => {
        loadComments();
    }, [articleId]);

    async function loadComments() {
        try {
            const data = await getComments(articleId);
            setComments(data);
        } catch (err) {
            console.error('Failed to load comments', err);
        } finally {
            setLoading(false);
        }
    }

    async function handleSubmit(e) {
        if (e) e.preventDefault();
        if (!newComment.trim() || isSubmitting) return;

        setIsSubmitting(true);
        try {
            await postComment(articleId, newComment, replyTo?.id);
            setNewComment('');
            setReplyTo(null);
            await loadComments();
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to post comment');
        } finally {
            setIsSubmitting(false);
        }
    }

    if (loading) return <div className={styles.loading}>Loading discussions...</div>;

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <MessageSquare size={16} />
                Discussions
            </div>

            <div className={styles.inputArea}>
                <form className={styles.form} onSubmit={handleSubmit}>
                    {replyTo && (
                        <div className={styles.replyingTo}>
                            <span>Replying to @{replyTo.username}</span>
                            <button type="button" onClick={() => setReplyTo(null)}>✕</button>
                        </div>
                    )}
                    <textarea
                        className={styles.textarea}
                        placeholder={replyTo ? "Write a reply..." : "Add to the discussion..."}
                        value={newComment}
                        onChange={(e) => setNewComment(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSubmit();
                            }
                        }}
                    />
                    <div className={styles.formActions}>
                        <div className={styles.hint}>Shift + Enter for new line</div>
                        <button
                            type="submit"
                            className={styles.sendBtn}
                            disabled={!newComment.trim() || isSubmitting}
                        >
                            {isSubmitting ? '...' : <Send size={14} />}
                        </button>
                    </div>
                </form>
            </div>

            <div className={styles.list}>
                {comments.length === 0 ? (
                    <div className={styles.empty}>No comments yet. Be the first to share your thoughts.</div>
                ) : (
                    comments.map(c => (
                        <CommentItem
                            key={c.id}
                            comment={c}
                            onReply={setReplyTo}
                            currentUserId={currentUserId}
                        />
                    ))
                )}
            </div>
        </div>
    );
}

function CommentItem({ comment, onReply, currentUserId, depth = 0 }) {
    const isAuthor = comment.user_id === currentUserId;

    return (
        <motion.div
            className={styles.item}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            style={{ marginLeft: depth > 0 ? 20 : 0 }}
        >
            <div className={styles.itemMajor}>
                <div className={styles.meta}>
                    <span className={styles.username}>@{comment.username}</span>
                    <span className={styles.dot}>•</span>
                    <span className={styles.time}>{formatDate(comment.created_at)}</span>
                    {isAuthor && <span className={styles.you}>YOU</span>}
                </div>
                <div className={styles.content}>
                    {comment.is_deleted ? <span className={styles.deleted}>[Deleted]</span> : comment.content}
                </div>
                <div className={styles.actions}>
                    {!comment.is_deleted && (
                        <button
                            className={styles.actionBtn}
                            onClick={() => onReply({ id: comment.id, username: comment.username })}
                        >
                            Reply
                        </button>
                    )}
                </div>
            </div>

            {comment.replies && comment.replies.map(r => (
                <div key={r.id} className={styles.replyWrapper}>
                    <div className={styles.replyLine} />
                    <CommentItem
                        comment={r}
                        onReply={onReply}
                        currentUserId={currentUserId}
                        depth={depth + 1}
                    />
                </div>
            ))}
        </motion.div>
    );
}
