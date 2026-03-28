import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';
const AUTH_TOKEN_KEY = 'ethos_access_token';
const AUTH_USER_KEY = 'ethos_user';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

function readStoredJSON(key) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

function writeStoredJSON(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function getAccessToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || '';
}

export function hasAccessToken() {
  return Boolean(getAccessToken());
}

export function getCurrentUser() {
  return readStoredJSON(AUTH_USER_KEY);
}

export function getCurrentUserId() {
  return getCurrentUser()?.id || '';
}

export function setAuthSession(authData = {}) {
  if (authData.access_token) {
    localStorage.setItem(AUTH_TOKEN_KEY, authData.access_token);
  }
  if (authData.user) {
    writeStoredJSON(AUTH_USER_KEY, authData.user);
  }
}

export function clearAuthSession() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

client.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function normalizeVerdict(classification = '') {
  const normalized = String(classification).toLowerCase();
  if (normalized === 'supported') return 'supported';
  if (normalized === 'contradicted') return 'contradicted';
  return 'not-mentioned';
}

function normalizeEvaluation(evaluation = {}) {
  const verdict = normalizeVerdict(evaluation.classification ?? evaluation.verdict);
  const rawConf = evaluation.confidence;
  return {
    claim: evaluation.claim ?? '',
    verdict,
    confidence: typeof rawConf === 'number' && rawConf >= 0 && rawConf <= 1
      ? rawConf
      : (verdict === 'not-mentioned' ? 0.5 : 0.75),
    evidence: evaluation.evidence ?? evaluation.explanation ?? '',
    supporting_urls: Array.isArray(evaluation.supporting_urls) ? evaluation.supporting_urls : [],
    source_types: Array.isArray(evaluation.source_types) ? evaluation.source_types : [],
  };
}

function normalizeFactCheckResponse(payload = {}) {
  const result = payload.result ?? payload;
  const evaluations = Array.isArray(result.evaluations)
    ? result.evaluations.map(normalizeEvaluation)
    : [];
  return {
    evaluations,
    unverifiable_ratio: typeof result.unverifiable_ratio === 'number' ? result.unverifiable_ratio : null,
    slop_score: typeof result.slop_score === 'number' ? result.slop_score : null,
    slop_label: result.slop_label ?? null,
  };
}

export async function getFeed() {
  const { data } = await client.get('/feed');
  return data.data ?? data;
}

export async function getPersonalizedFeed(userId = getCurrentUserId()) {
  if (!userId) throw new Error('No authenticated user found.');
  const { data } = await client.get(`/personalized_feed/${userId}`);
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

export async function getRephrase(id) {
  const { data } = await client.get(`/article/${id}/rephrase`, {
    timeout: 45000,
  });
  return data;
}

export async function generatePNC(naturalLanguage, userId = getCurrentUserId()) {
  if (!userId) throw new Error('No authenticated user found.');
  const { data } = await client.post('/pnc/generate', {
    natural_language: naturalLanguage,
    user_id: userId,
  });
  return data;
}

export async function getPNC(userId = getCurrentUserId()) {
  if (!userId) throw new Error('No authenticated user found.');
  const { data } = await client.get(`/pnc/${userId}`);
  return data;
}

export async function savePNC(pncData, userId = getCurrentUserId()) {
  if (!userId) throw new Error('No authenticated user found.');
  const { data } = await client.post(`/pnc/${userId}`, pncData);
  return data;
}

export async function getLeaderboard(limit = 10) {
  const { data } = await client.get(`/leaderboard/top?limit=${limit}`);
  return data;
}

export async function recordEvent(articleId, timeSpentSecs) {
  const userId = getCurrentUserId();
  if (!userId) throw new Error('No authenticated user found.');

  const { data } = await client.post('/leaderboard/event', {
    user_id: userId,
    article_id: articleId,
    time_spent_secs: timeSpentSecs,
  });
  return data;
}

export async function signup(payload) {
  const { data } = await client.post('/auth/signup', payload);
  setAuthSession(data);
  return data;
}

export async function login(payload) {
  const { data } = await client.post('/auth/login', payload);
  setAuthSession(data);
  return data;
}

export async function getMe() {
  const { data } = await client.get('/auth/me');
  writeStoredJSON(AUTH_USER_KEY, data);
  return data;
}
