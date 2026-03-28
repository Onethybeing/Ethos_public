import axios from 'axios';

export const USER_ID = 'demo_user';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

function normalizeVerdict(classification = '') {
  const normalized = String(classification).toLowerCase();
  if (normalized === 'supported') return 'supported';
  if (normalized === 'contradicted') return 'contradicted';
  return 'not-mentioned';
}

function normalizeEvaluation(evaluation = {}) {
  const verdict = normalizeVerdict(evaluation.classification ?? evaluation.verdict);
  return {
    claim: evaluation.claim ?? '',
    verdict,
    confidence: typeof evaluation.confidence === 'number'
      ? evaluation.confidence
      : (verdict === 'not-mentioned' ? 0.5 : 0.75),
    evidence: evaluation.evidence ?? evaluation.explanation ?? '',
    supporting_urls: Array.isArray(evaluation.supporting_urls) ? evaluation.supporting_urls : [],
  };
}

function normalizeFactCheckResponse(payload = {}) {
  const result = payload.result ?? payload;
  const evaluations = Array.isArray(result.evaluations)
    ? result.evaluations.map(normalizeEvaluation)
    : [];
  return {
    ...result,
    evaluations,
  };
}

export async function getFeed() {
  const { data } = await client.get('/feed');
  return data.data ?? data;
}

export async function getPersonalizedFeed() {
  const { data } = await client.get(`/personalized_feed/${USER_ID}`);
  return data.data ?? data;
}

export async function getArticle(id) {
  const { data } = await client.get(`/article/${id}`);
  return data.data ?? data;
}

export async function factCheckArticle(id) {
  const { data } = await client.post(`/article/${id}/fact-check`, undefined, {
    timeout: 60000,
  });
  return normalizeFactCheckResponse(data);
}

export async function factCheckText(text) {
  const { data } = await client.post('/fact-check', { text }, {
    timeout: 60000,
  });
  return normalizeFactCheckResponse(data);
}

export async function getClusters(id) {
  const { data } = await client.get(`/article/${id}/clusters`);
  return data;
}

export async function generatePNC(naturalLanguage) {
  const { data } = await client.post('/pnc/generate', {
    natural_language: naturalLanguage,
    user_id: USER_ID,
  });
  return data;
}

export async function getPNC() {
  const { data } = await client.get(`/pnc/${USER_ID}`);
  return data;
}

export async function savePNC(pncData) {
  const { data } = await client.post(`/pnc/${USER_ID}`, pncData);
  return data;
}

export async function getLeaderboard(limit = 10) {
  const { data } = await client.get(`/leaderboard/top?limit=${limit}`);
  return data;
}

export async function recordEvent(articleId, timeSpentSecs) {
  const { data } = await client.post('/leaderboard/event', {
    user_id: USER_ID,
    article_id: articleId,
    time_spent_secs: timeSpentSecs,
  });
  return data;
}
