const API_BASE = 'http://localhost:8001/api';

/**
 * API service for Narrative Memory System
 */
export const api = {
    // ================== Retrieval ==================

    async search(query, options = {}) {
        const response = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                image_url: options.imageUrl || null,
                limit: options.limit || 10,
                time_filter_days: options.timeFilterDays || null
            })
        });
        return response.json();
    },

    async fullPipeline(query, options = {}) {
        const response = await fetch(`${API_BASE}/retrieve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                image_url: options.imageUrl || null,
                counter_narrative: options.counterNarrative || null,
                time_filter_days: options.timeFilterDays || 30,
                top_k: options.topK || 10
            })
        });
        return response.json();
    },

    async discover(positiveTexts, negativeTexts = []) {
        const response = await fetch(`${API_BASE}/discover`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                positive_texts: positiveTexts,
                negative_texts: negativeTexts,
                limit: 20
            })
        });
        return response.json();
    },

    async findMutations(narrativeId, text) {
        const response = await fetch(`${API_BASE}/detect-mutations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                narrative_id: narrativeId || null,
                text: text || null
            })
        });
        return response.json();
    },

    async generateReport(topic, days = 30) {
        const response = await fetch(`${API_BASE}/report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, days })
        });
        return response.json();
    },

    // ================== Ingestion ==================

    async triggerIngestion() {
        const response = await fetch(`${API_BASE}/ingest`, {
            method: 'POST',
        });
        return response.json();
    },

    async getIngestionStatus() {
        const response = await fetch(`${API_BASE}/ingest/status`);
        return response.json();
    },

    async generateAnchors() {
        const response = await fetch(`${API_BASE}/anchors/generate`, {
            method: 'POST'
        });
        return response.json();
    },

    // ================== Enrichment ==================

    async triggerEnrichment(batchSize = 20, maxArticles = null) {
        const response = await fetch(`${API_BASE}/enrich`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                batch_size: batchSize,
                max_articles: maxArticles
            })
        });
        return response.json();
    },

    async getEnrichmentStatus() {
        const response = await fetch(`${API_BASE}/enrich/status`);
        return response.json();
    },

    // ================== Memory ==================

    async runDecay(decayLambda = null, fadeThreshold = null) {
        const response = await fetch(`${API_BASE}/decay`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                decay_lambda: decayLambda,
                fade_threshold: fadeThreshold
            })
        });
        return response.json();
    },

    async getDecayPreview(sampleSize = 20) {
        const response = await fetch(`${API_BASE}/decay/preview?sample_size=${sampleSize}`);
        return response.json();
    },

    async getMemoryStats() {
        const response = await fetch(`${API_BASE}/stats`);
        return response.json();
    },

    async getFamilies(minSize = 2, includeFaded = false) {
        const response = await fetch(`${API_BASE}/families?min_size=${minSize}&include_faded=${includeFaded}`);
        return response.json();
    },

    async detectDrift(threshold = 0.85) {
        const response = await fetch(`${API_BASE}/drift/detect`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ threshold })
        });
        return response.json();
    },

    async createSnapshot(name) {
        const response = await fetch(`${API_BASE}/snapshot/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        return response.json();
    },

    async listSnapshots() {
        const response = await fetch(`${API_BASE}/snapshot/list`);
        return response.json();
    },

    // ================== Health ==================

    async getHealth() {
        const response = await fetch(`${API_BASE}/health`);
        return response.json();
    }
};

export default api;
