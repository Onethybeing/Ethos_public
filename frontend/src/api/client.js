import axios from 'axios';

export const USER_ID = 'demo_user';

const client = axios.create({
  baseURL: '',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

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
  const { data } = await client.post(`/article/${id}/fact-check`);
  return data;
}

export async function factCheckText(text) {
  const { data } = await client.post('/fact-check', { text });
  return data;
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
