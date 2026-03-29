export function timeAgo(isoString) {
  const seconds = (Date.now() - new Date(isoString).getTime()) / 1000;
  if (seconds < 60)   return `${Math.floor(seconds)}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'long', year: 'numeric',
  });
}

export function slopColor(score) {
  if (typeof score !== 'number' || Number.isNaN(score)) return '#7a6f63';
  if (score < 0.3) return '#1a7a52';
  if (score < 0.7) return '#b5830a';
  return '#c8281e';
}

export function slopLabel(score) {
  if (typeof score !== 'number' || Number.isNaN(score)) return 'Insufficient';
  if (score < 0.3) return 'Human';
  if (score < 0.7) return 'Mixed';
  return 'AI Slop';
}

export function catColor(category) {
  const map = {
    Technology: '#2a4a8a',
    Politics:   '#c8281e',
    Science:    '#6b3fa0',
    Finance:    '#b5830a',
    Health:     '#1a7a52',
    Policy:     '#1a5a6a',
  };
  return map[category] || '#7a6f63';
}

export function catEmoji(category) {
  const map = {
    Technology: '⚡',
    Politics:   '⚖️',
    Science:    '🔬',
    Finance:    '📈',
    Health:     '🧬',
    Policy:     '📋',
  };
  return map[category] || '📰';
}

export function verdictColor(verdict) {
  if (verdict === 'supported')    return '#1a7a52';
  if (verdict === 'contradicted') return '#c8281e';
  return '#b5830a';
}

export function verdictLabel(verdict) {
  if (verdict === 'supported')    return 'Supported';
  if (verdict === 'contradicted') return 'Contradicted';
  return 'Unverified';
}

export function avatarBg(userId) {
  const palette = [
    '#2a4a8a', '#6b3fa0', '#b5830a', '#1a7a52',
    '#c8281e', '#1a5a6a', '#7a3f20', '#3a6a2a',
  ];
  let hash = 0;
  for (const c of String(userId)) {
    hash = (hash * 31 + c.charCodeAt(0)) & 0xffffffff;
  }
  return palette[Math.abs(hash) % palette.length];
}

export function initials(userId) {
  return String(userId)
    .split('_')
    .map(w => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

export function toRoman(n) {
  const map = [[1000,'M'],[900,'CM'],[500,'D'],[400,'CD'],[100,'C'],[90,'XC'],
               [50,'L'],[40,'XL'],[10,'X'],[9,'IX'],[5,'V'],[4,'IV'],[1,'I']];
  let result = '';
  for (const [val, sym] of map) {
    while (n >= val) { result += sym; n -= val; }
  }
  return result;
}
