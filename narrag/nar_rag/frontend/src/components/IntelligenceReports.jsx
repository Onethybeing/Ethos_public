import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { FileText, Send, Download, Loader, Calendar, TrendingUp, AlertTriangle } from 'lucide-react';
import api from '../services/api';

/**
 * IntelligenceReports - Generate strategic narrative intelligence briefings
 * 
 * Uses the MetaSynthesis Agent to combine:
 * 1. Dominance Analysis (what narratives are winning)
 * 2. Conflict Detection (where narratives compete)
 * 3. Evolution Tracking (how the landscape changed)
 * 4. Outcome Prediction (what history says happens next)
 */
function IntelligenceReports() {
    const [topic, setTopic] = useState('');
    const [days, setDays] = useState(30);
    const [loading, setLoading] = useState(false);
    const [report, setReport] = useState(null);
    const [error, setError] = useState(null);

    const handleGenerate = async (e) => {
        e.preventDefault();
        if (!topic.trim()) return;

        setLoading(true);
        setError(null);
        setReport(null);

        try {
            const data = await api.generateReport(topic, days);
            if (data.error) {
                setError(data.error);
            } else {
                setReport(data);
            }
        } catch (err) {
            setError('Report generation failed. Check backend connection.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const downloadReport = () => {
        if (!report?.final_report_markdown) return;
        const blob = new Blob([report.final_report_markdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `narrative-intel-${topic.replace(/\s+/g, '-').toLowerCase()}-${new Date().toISOString().split('T')[0]}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="grid gap-6">
            {/* Input Form */}
            <div className="card">
                <div className="flex items-center gap-3 mb-4">
                    <FileText size={24} className="text-primary" />
                    <div>
                        <h2 className="text-xl font-bold">Strategic Intelligence Report</h2>
                        <p className="text-sm text-secondary">Generate comprehensive narrative landscape analysis</p>
                    </div>
                </div>

                <form onSubmit={handleGenerate} className="grid md:grid-cols-[1fr_120px_auto] gap-4 items-end">
                    <div>
                        <label className="text-sm text-secondary block mb-1">Topic</label>
                        <input
                            type="text"
                            className="input w-full"
                            placeholder="e.g., Artificial Intelligence, Climate Policy, Tech Layoffs..."
                            value={topic}
                            onChange={(e) => setTopic(e.target.value)}
                        />
                    </div>
                    <div>
                        <label className="text-sm text-secondary block mb-1">Period</label>
                        <select
                            className="input w-full"
                            value={days}
                            onChange={(e) => setDays(Number(e.target.value))}
                        >
                            <option value={7}>7 Days</option>
                            <option value={30}>30 Days</option>
                            <option value={90}>90 Days</option>
                        </select>
                    </div>
                    <button type="submit" className="btn btn-primary" disabled={loading}>
                        {loading ? <Loader size={18} className="animate-spin" /> : <Send size={18} />}
                        Generate
                    </button>
                </form>
            </div>

            {/* Error */}
            {error && (
                <div className="card border-l-4 border-error bg-error/10">
                    <AlertTriangle size={18} className="inline mr-2" />
                    {error}
                </div>
            )}

            {/* Report Output */}
            {report && (
                <div className="grid gap-4 fade-in">
                    {/* Quick Stats */}
                    <div className="grid grid-3 gap-4">
                        <QuickStat
                            icon={Calendar}
                            label="Period"
                            value={report.period}
                        />
                        <QuickStat
                            icon={TrendingUp}
                            label="Dominant Narrative"
                            value={report.dominance_analysis?.[0]?.framing || "None"}
                            truncate
                        />
                        <QuickStat
                            icon={AlertTriangle}
                            label="Conflicts"
                            value={`${report.conflicts?.length || 0} detected`}
                        />
                    </div>

                    {/* Dominance Breakdown */}
                    {report.dominance_analysis && report.dominance_analysis.length > 0 && (
                        <div className="card">
                            <h3 className="mb-4">Narrative Dominance</h3>
                            <div className="space-y-3">
                                {report.dominance_analysis.slice(0, 5).map((d, idx) => (
                                    <div key={idx} className="flex items-center gap-3">
                                        <div className="w-32 truncate text-sm font-medium">{d.framing}</div>
                                        <div className="flex-1 h-3 bg-surface-2 rounded overflow-hidden">
                                            <div
                                                className="h-full bg-primary"
                                                style={{ width: `${Math.min(d.metrics.prevalence * 100, 100)}%` }}
                                            />
                                        </div>
                                        <div className="w-16 text-xs text-secondary">
                                            {(d.metrics.prevalence * 100).toFixed(0)}%
                                        </div>
                                        <div className={`tag text-xs ${d.status === 'Rising' ? 'tag-warning' :
                                                d.status === 'Dominant' ? 'tag-primary' : ''
                                            }`}>
                                            {d.status}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Full Markdown Report */}
                    <div className="card relative">
                        <button
                            onClick={downloadReport}
                            className="absolute top-4 right-4 btn btn-secondary btn-sm"
                        >
                            <Download size={16} />
                            Download
                        </button>

                        <h3 className="mb-4">Full Intelligence Brief</h3>
                        <div className="prose prose-invert max-w-none">
                            <ReactMarkdown>
                                {report.final_report_markdown || "No report content generated."}
                            </ReactMarkdown>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

const QuickStat = ({ icon: Icon, label, value, truncate }) => (
    <div className="card bg-surface-2">
        <div className="flex items-center gap-2 mb-1">
            <Icon size={14} className="text-secondary" />
            <span className="text-xs text-secondary uppercase">{label}</span>
        </div>
        <div className={`font-bold ${truncate ? 'truncate' : ''}`}>{value}</div>
    </div>
);

export default IntelligenceReports;
