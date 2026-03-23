import { useState } from 'react';
import { Search, GitBranch, TrendingUp, AlertTriangle, ExternalLink, CheckCircle, XCircle, Sparkles } from 'lucide-react';
import api from '../services/api';

/**
 * NarrativeAnalyzer - The main analysis tool
 * 
 * Features:
 * 1. Semantic Search (find similar narratives in memory)
 * 2. Mutation Detection (track how narratives evolve/spin)
 * 3. Outcome Prediction (what happened historically when this pattern appeared)
 */
function NarrativeAnalyzer() {
    const [query, setQuery] = useState('');
    const [mode, setMode] = useState('search'); // 'search' | 'mutation' | 'outcome'
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState(null);
    const [error, setError] = useState(null);

    const handleAnalyze = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError(null);
        setResults(null);

        try {
            let data;
            if (mode === 'search') {
                data = await api.fullPipeline(query, { topK: 10 });
                data._mode = 'search';
            } else if (mode === 'mutation') {
                data = await api.findMutations(null, query);
                data._mode = 'mutation';
            }
            setResults(data);
        } catch (err) {
            setError('Analysis failed. Check backend connection.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="grid gap-6">
            {/* Input Section */}
            <div className="card">
                <h2 className="text-xl font-bold mb-4">Narrative Analysis</h2>

                {/* Mode Selector */}
                <div className="flex gap-2 mb-4">
                    <ModeButton
                        active={mode === 'search'}
                        onClick={() => setMode('search')}
                        icon={Search}
                        label="Search Memory"
                    />
                    <ModeButton
                        active={mode === 'mutation'}
                        onClick={() => setMode('mutation')}
                        icon={GitBranch}
                        label="Detect Mutations"
                    />
                </div>

                {/* Search Input */}
                <form onSubmit={handleAnalyze} className="flex gap-2">
                    <input
                        type="text"
                        className="input flex-1"
                        placeholder={
                            mode === 'search'
                                ? "Enter a narrative topic or paste article text..."
                                : "Enter text to find mutations/spin variants..."
                        }
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                    <button type="submit" className="btn btn-primary" disabled={loading}>
                        {loading ? <span className="spinner" /> : <Search size={18} />}
                        Analyze
                    </button>
                </form>

                {/* Mode Description */}
                <p className="text-sm text-secondary mt-3">
                    {mode === 'search' && "Finds semantically similar narratives using hybrid vector search (dense + sparse + RRF fusion)."}
                    {mode === 'mutation' && "Detects how this narrative has been 'spun' or evolved over time. Uses Qdrant Discovery API."}
                </p>
            </div>

            {/* Error Display */}
            {error && (
                <div className="card border-l-4 border-error bg-error/10">
                    <AlertTriangle size={18} className="inline mr-2" />
                    {error}
                </div>
            )}

            {/* Results */}
            {results && results._mode === 'search' && <SearchResults data={results} />}
            {results && results._mode === 'mutation' && <MutationResults data={results} />}
        </div>
    );
}

// ----- SUB-COMPONENTS -----

const ModeButton = ({ active, onClick, icon: Icon, label }) => (
    <button
        onClick={onClick}
        className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${active ? 'bg-primary text-white' : 'bg-surface-2 text-secondary hover:text-white'
            }`}
    >
        <Icon size={16} />
        {label}
    </button>
);

const SearchResults = ({ data }) => {
    if (!data.results || data.results.length === 0) {
        return <div className="card text-secondary">No matching narratives found.</div>;
    }

    return (
        <div className="grid gap-4">
            {/* Outcome Prediction Banner */}
            {data.outcomes && data.outcomes.length > 0 && (
                <div className="card border-l-4 border-warning bg-warning/5">
                    <div className="flex items-center gap-2 mb-2">
                        <TrendingUp size={18} className="text-warning" />
                        <span className="font-bold">Outcome Prediction</span>
                    </div>
                    <p className="text-sm">{data.prediction_summary || "Historical patterns detected."}</p>
                    <p className="text-xs text-secondary mt-1">
                        Based on {data.outcomes.length} historical precedent(s).
                    </p>
                </div>
            )}

            {/* Results Grid */}
            <div className="card">
                <h3 className="mb-4">Pattern Matches ({data.results.length})</h3>
                <div className="grid grid-2 gap-4">
                    {data.results.map((result, idx) => (
                        <div key={idx} className="card card-glass">
                            {/* Header: source, date, score */}
                            <div className="flex justify-between items-start mb-2">
                                <span className="text-xs text-secondary">
                                    {result.payload.source} · {new Date(result.payload.timestamp * 1000).toLocaleDateString()}
                                </span>
                                <div className="flex items-center gap-2">
                                    {result.payload.enriched && (
                                        <span className="tag tag-success text-xs" title="Enriched via LLM">
                                            <Sparkles size={10} className="inline mr-1" />
                                            Enriched
                                        </span>
                                    )}
                                    {result.payload.link_alive === false && (
                                        <span className="tag tag-error text-xs" title="Source link is dead">
                                            <XCircle size={10} className="inline mr-1" />
                                            Dead
                                        </span>
                                    )}
                                    <span className="tag tag-primary text-xs">
                                        {(result.score * 100).toFixed(0)}%
                                    </span>
                                </div>
                            </div>

                            {/* Title + link */}
                            <h4 className="font-bold mb-1">
                                {result.payload.url ? (
                                    <a href={result.payload.url} target="_blank" rel="noopener noreferrer"
                                        className="hover:text-primary transition-colors inline-flex items-center gap-1">
                                        {result.payload.title}
                                        <ExternalLink size={12} className="opacity-50" />
                                    </a>
                                ) : result.payload.title}
                            </h4>

                            {/* Summary (from enrichment) or fallback */}
                            {result.payload.summary ? (
                                <p className="text-sm opacity-70 mb-2 line-clamp-3">{result.payload.summary}</p>
                            ) : (
                                <p className="text-xs text-secondary italic mb-2">Not yet enriched</p>
                            )}

                            {/* Narrative fields (only if enriched) */}
                            {result.payload.enriched && (
                                <div className="text-xs space-y-1 border-t border-white/10 pt-2 mt-2">
                                    {result.payload.narrative_framing && (
                                        <div><span className="text-secondary">Framing:</span> {result.payload.narrative_framing}</div>
                                    )}
                                    {result.payload.actor_roles && typeof result.payload.actor_roles === 'object' && (
                                        <div>
                                            <span className="text-secondary">Actors:</span>{' '}
                                            {Object.entries(result.payload.actor_roles).slice(0, 3).map(([actor, role]) => (
                                                <span key={actor} className="inline-block mr-2">
                                                    <strong>{actor}</strong>: {role}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Tags */}
                            <div className="flex flex-wrap gap-1 mt-2">
                                {result.payload.tags?.slice(0, 5).map(tag => (
                                    <span key={tag} className="tag text-xs">{tag}</span>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Provenance */}
            {data.provenance && (
                <div className="text-xs text-secondary text-right">
                    Query completed in {data.provenance.total_ms}ms
                </div>
            )}
        </div>
    );
};

const MutationResults = ({ data }) => {
    if (!data.mutations || data.mutations.length === 0) {
        return (
            <div className="card">
                <p className="text-secondary">No mutations detected for this narrative.</p>
                <p className="text-xs mt-2">This could mean the narrative hasn't evolved significantly in memory.</p>
            </div>
        );
    }

    return (
        <div className="grid gap-4">
            {/* Hotspot Alert */}
            {data.hotspot_alert && (
                <div className="card border-l-4 border-error bg-error/10">
                    <AlertTriangle size={18} className="inline mr-2 text-error" />
                    <span className="font-bold">COORDINATED NARRATIVE DETECTED</span>
                    <p className="text-sm mt-1">High mutation frequency suggests coordinated messaging or rapid spin.</p>
                </div>
            )}

            {/* Original Narrative */}
            <div className="card">
                <h3 className="mb-2">Original Narrative</h3>
                <div className="p-3 bg-surface-2 rounded-lg">
                    <div className="font-bold">{data.original_narrative.framing}</div>
                    <div className="text-sm text-secondary">Tone: {data.original_narrative.tone}</div>
                </div>
            </div>

            {/* Mutation Timeline */}
            <div className="card">
                <h3 className="mb-4">Detected Mutations ({data.mutations.length})</h3>
                <div className="space-y-4">
                    {data.mutations.map((mut, idx) => (
                        <div key={idx} className="border-l-2 border-primary pl-4 py-2">
                            <div className="flex justify-between items-start">
                                <span className="tag tag-warning text-xs">{mut.type}</span>
                                <span className="text-xs text-secondary">
                                    Severity: {mut.severity}/10
                                </span>
                            </div>
                            <p className="text-sm mt-2">{mut.explanation}</p>
                            <p className="text-xs text-secondary mt-1 line-clamp-1">
                                "{mut.variant_text}"
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default NarrativeAnalyzer;
