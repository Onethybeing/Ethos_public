import { useState, useEffect } from 'react';
import { Database, Activity, Archive, Play, RefreshCw, CheckCircle, XCircle, Sparkles, Link2 } from 'lucide-react';
import api from '../services/api';

/**
 * SystemDashboard - Memory status and system controls
 * 
 * Features:
 * 1. Qdrant collection stats (total points, active, faded, enriched)
 * 2. Ingestion controls (trigger new data collection - fast mode)
 * 3. Enrichment controls (trigger batch LLM enrichment)
 * 4. Memory decay simulation
 * 5. Source distribution
 */
function SystemDashboard() {
    const [stats, setStats] = useState(null);
    const [health, setHealth] = useState(null);
    const [ingestionStatus, setIngestionStatus] = useState(null);
    const [enrichmentStatus, setEnrichmentStatus] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
        const interval = setInterval(loadData, 10000); // Refresh every 10s
        return () => clearInterval(interval);
    }, []);

    const loadData = async () => {
        try {
            const [s, h, i, e] = await Promise.all([
                api.getMemoryStats().catch(() => null),
                api.getHealth().catch(() => ({ status: 'error' })),
                api.getIngestionStatus().catch(() => null),
                api.getEnrichmentStatus().catch(() => null)
            ]);
            setStats(s);
            setHealth(h);
            setIngestionStatus(i);
            setEnrichmentStatus(e);
        } catch (err) {
            console.error('Failed to load dashboard data:', err);
        } finally {
            setLoading(false);
        }
    };

    const triggerIngestion = async () => {
        await api.triggerIngestion();
        loadData();
    };

    const triggerEnrichment = async () => {
        await api.triggerEnrichment(20);
        loadData();
    };

    const runDecay = async () => {
        if (confirm("Run memory decay? This will fade old/weak memories.")) {
            await api.runDecay();
            loadData();
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="spinner" />
            </div>
        );
    }

    return (
        <div className="grid gap-6">
            {/* Health Status */}
            <div className="card">
                <h2 className="text-xl font-bold mb-4">System Health</h2>
                <div className="flex items-center gap-3">
                    {health?.status === 'healthy' ? (
                        <>
                            <CheckCircle size={24} className="text-success" />
                            <div>
                                <div className="font-bold text-success">Online</div>
                                <div className="text-sm text-secondary">
                                    Qdrant: {health.qdrant?.collection} ({health.qdrant?.points_count} points)
                                </div>
                            </div>
                        </>
                    ) : (
                        <>
                            <XCircle size={24} className="text-error" />
                            <div>
                                <div className="font-bold text-error">Offline</div>
                                <div className="text-sm text-secondary">{health?.error || 'Connection failed'}</div>
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Stats Grid */}
            {stats && (
                <div className="grid grid-4 gap-4">
                    <StatCard icon={Database} label="Total Memories" value={stats.total_points} color="text-info" />
                    <StatCard icon={Activity} label="Active" value={stats.active} color="text-success" />
                    <StatCard icon={Archive} label="Faded" value={stats.faded} color="text-secondary" />
                    <StatCard icon={Sparkles} label="Enriched" value={stats.enriched ?? '-'} color="text-warning" />
                </div>
            )}

            <div className="grid grid-2 gap-6">
                {/* Controls */}
                <div className="card">
                    <h3 className="mb-4">Ingestion</h3>
                    <div className="flex flex-col gap-3">
                        <button
                            onClick={triggerIngestion}
                            disabled={ingestionStatus?.running}
                            className={`btn ${ingestionStatus?.running ? 'btn-secondary' : 'btn-primary'} w-full`}
                        >
                            <Play size={16} />
                            {ingestionStatus?.running ? 'Ingestion Running...' : 'Run Ingestion'}
                        </button>
                        <p className="text-xs text-secondary">
                            Collects articles from 21 RSS/API sources. Stores metadata + embeddings (no LLM).
                        </p>
                    </div>

                    {ingestionStatus?.last_run && (
                        <div className="mt-4 text-sm text-secondary border-t border-white/10 pt-3">
                            <div>Last run: {new Date(ingestionStatus.last_run).toLocaleString()}</div>
                            <div>New items: {ingestionStatus.last_stats?.new || 0}</div>
                            <div>Reinforced: {ingestionStatus.last_stats?.reinforced || 0}</div>
                        </div>
                    )}
                </div>

                {/* Enrichment Controls */}
                <div className="card">
                    <h3 className="mb-4">Enrichment</h3>
                    <div className="flex flex-col gap-3">
                        <button
                            onClick={triggerEnrichment}
                            disabled={enrichmentStatus?.running}
                            className={`btn ${enrichmentStatus?.running ? 'btn-secondary' : 'btn-primary'} w-full`}
                        >
                            <Sparkles size={16} />
                            {enrichmentStatus?.running ? 'Enrichment Running...' : 'Enrich Articles (LLM)'}
                        </button>
                        <button onClick={runDecay} className="btn btn-secondary w-full">
                            <Archive size={16} />
                            Simulate Memory Decay
                        </button>
                        <p className="text-xs text-secondary">
                            Scrapes article text, generates summaries &amp; narrative tags via Gemini LLM in batches of 20.
                        </p>
                    </div>

                    {enrichmentStatus?.last_run && (
                        <div className="mt-4 text-sm text-secondary border-t border-white/10 pt-3">
                            <div>Last run: {new Date(enrichmentStatus.last_run).toLocaleString()}</div>
                            {enrichmentStatus.last_stats?.error ? (
                                <div className="text-error">Error: {enrichmentStatus.last_stats.error}</div>
                            ) : (
                                <>
                                    <div>Processed: {enrichmentStatus.last_stats?.total_processed || 0}</div>
                                    <div>Enriched: {enrichmentStatus.last_stats?.total_enriched || 0}</div>
                                    <div>Dead links: {enrichmentStatus.last_stats?.total_dead_links || 0}</div>
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Source Distribution */}
            <div className="grid grid-1 gap-6">
                {stats?.sources && (
                    <div className="card">
                        <h3 className="mb-4">Data Sources</h3>
                        <div className="space-y-2">
                            {Object.entries(stats.sources)
                                .sort(([, a], [, b]) => b - a)
                                .map(([source, count]) => (
                                    <div key={source} className="flex justify-between items-center">
                                        <span className="text-sm truncate">{source}</span>
                                        <div className="flex items-center gap-2">
                                            <div
                                                className="h-2 bg-primary rounded"
                                                style={{ width: `${Math.min(count / 10, 100)}px` }}
                                            />
                                            <span className="text-xs text-secondary w-8 text-right">{count}</span>
                                        </div>
                                    </div>
                                ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

const StatCard = ({ icon: Icon, label, value, color }) => (
    <div className="card text-center">
        <div className={`inline-flex p-3 rounded-full bg-surface-2 mb-3 ${color}`}>
            <Icon size={24} />
        </div>
        <div className="text-2xl font-bold">{value ?? '-'}</div>
        <div className="text-sm text-secondary">{label}</div>
    </div>
);

export default SystemDashboard;
