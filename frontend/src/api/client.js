import axios from 'axios';

export const API_BASE = 'http://localhost:8000';
export const USER_ID = 'demo_user';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

/* ════════════════════════════════
   MOCK DATA
════════════════════════════════ */
export const MOCK_ARTICLES = [
  {
    id: 'art001',
    title: 'OpenAI Ships GPT-5 With Recursive Self-Verification Architecture',
    content: `OpenAI has released GPT-5 to select enterprise customers, introducing a recursive reasoning loop allowing the model to audit and revise its own outputs before delivery. Internal benchmarks claim a 43% improvement on MATH competitions and near-doubling of accuracy on HumanEval coding tasks versus GPT-4.\n\nThe deployment has immediately prompted concern from AI safety researchers who argue that self-verifying systems introduce novel, potentially undetectable failure modes. "We are now in territory where the model's confidence in its own outputs may diverge significantly from actual correctness," wrote one researcher in a widely-shared thread.\n\nCEO Sam Altman confirmed the phased rollout in a post on X, citing the need to observe real-world behaviour before wider release. The model is currently available to roughly 400 enterprise accounts under a strict confidentiality agreement.`,
    source: 'TechCrunch', url: '#', image_url: null,
    published_at: new Date(Date.now() - 45 * 60000).toISOString(),
    category: 'Technology', ai_slop_score: 0.11,
  },
  {
    id: 'art002',
    title: '147 Nations Ratify Historic Carbon Pricing Floor at Geneva',
    content: `After three weeks of fractious negotiations, delegates from 147 countries signed an agreement establishing a minimum carbon price of $75 per metric ton by 2027. The deal, brokered under UN auspices, includes a first-of-its-kind enforcement mechanism allowing signatory nations to impose retaliatory tariffs on goods from non-compliant states.\n\nClimate scientists cautiously welcomed the agreement while noting that the floor remains below the $150 threshold economists argue is necessary to meet 1.5°C targets. The deal is widely seen as a political compromise driven by a coalition of small island nations, the EU, and a surprise last-minute concession from China.\n\n"It is an imperfect instrument that is nonetheless real," said Dr. Fatima Al-Rashid of the Climate Analytics Institute. "The enforcement clause is unprecedented and that alone changes the calculus."`,
    source: 'Reuters', url: '#', image_url: null,
    published_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    category: 'Politics', ai_slop_score: 0.06,
  },
  {
    id: 'art003',
    title: 'Federal Reserve Signals Three Cuts as Inflation Retreats to 2.1%',
    content: `Federal Reserve Chair Jerome Powell indicated the central bank is prepared to lower interest rates three times this year after fresh CPI data showed inflation declining to 2.1%, within striking distance of the 2% mandate. Markets responded with a 1.4% rally in the S&P 500 and a broad retreat in Treasury yields.\n\nAnalysts warn that service-sector inflation remains stubborn and the labour market continues to defy expectations, printing another 187,000 non-farm payrolls in January. Several Fed governors have publicly cautioned against premature easing, and futures markets have rapidly revised their odds of a March cut downward to 28% from 61% just two weeks ago.`,
    source: 'Bloomberg', url: '#', image_url: null,
    published_at: new Date(Date.now() - 3.5 * 3600000).toISOString(),
    category: 'Finance', ai_slop_score: 0.15,
  },
  {
    id: 'art004',
    title: 'CRISPR Base-Editing Trial Restores Vision in 11 of 14 Participants',
    content: `A Phase II clinical trial using a next-generation CRISPR-Cas12 base editor has restored functional vision in 11 of 14 participants with Leber congenital amaurosis type 10. The results, published in Nature Medicine, represent the first time in-vivo base editing has achieved statistically significant visual recovery in a randomised controlled setting.\n\nResearchers at the Broad Institute and University College London collaborated on the study, delivering the editing machinery via adeno-associated viral vectors directly to photoreceptor cells. "We are watching a technology transition from proof-of-concept to genuine medicine," said lead author Dr. Sarah Chen in a press briefing. Side effects were mild and transient in all participants.`,
    source: 'Nature News', url: '#', image_url: null,
    published_at: new Date(Date.now() - 8 * 3600000).toISOString(),
    category: 'Science', ai_slop_score: 0.08,
  },
  {
    id: 'art005',
    title: 'EU AI Liability Directive Creates Sweeping New Corporate Obligations',
    content: `The European Parliament passed the AI Liability Directive with a 421-to-183 vote, requiring companies deploying high-risk AI systems to maintain detailed decision logs for a minimum of seven years and grant affected parties the right to algorithmic explanations within 30 days of request.\n\nThe law takes effect in 18 months and applies to any firm serving EU customers regardless of where the AI system was developed, trained, or deployed — a scope that legal experts compare to GDPR's extraterritorial reach. Companies face fines of up to 3% of global annual revenue for non-compliance, with a 6% threshold for systematic violations.`,
    source: 'Politico Europe', url: '#', image_url: null,
    published_at: new Date(Date.now() - 14 * 3600000).toISOString(),
    category: 'Policy', ai_slop_score: 0.09,
  },
  {
    id: 'art006',
    title: '10 SHOCKING Facts About AI That Will Change EVERYTHING You Know!!',
    content: `Artificial intelligence is literally transforming every single aspect of modern life in ways you absolutely cannot imagine! Did you know that AI can now predict the stock market with 99% accuracy? Here are ten mind-blowing facts that top experts don't want you to discover about how AI is revolutionising your daily existence. The future is already here and it is truly unbelievable. You will not believe what number seven reveals about your smartphone! This information is being suppressed by major tech companies. Share this article before it gets taken down!`,
    source: 'ViralTechHub', url: '#', image_url: null,
    published_at: new Date(Date.now() - 20 * 60000).toISOString(),
    category: 'Technology', ai_slop_score: 0.93,
  },
  {
    id: 'art007',
    title: 'SpaceX Starship Achieves Mars Transfer Orbit on Fifth Integrated Flight',
    content: `SpaceX's Starship Vehicle 32 successfully achieved Mars transfer orbit Thursday, marking a pivotal milestone in the company's interplanetary programme. The uncrewed mission carries 42 tonnes of scientific instruments and a pre-positioned propellant cache intended to support a future crewed landing attempt.\n\nMission controllers at the Starbase facility in Boca Chica confirmed all six Raptor engines performed nominally throughout the seven-minute trans-Mars injection burn. The vehicle is expected to reach Mars proximity in approximately seven months, where it will attempt an aerocapture manoeuvre that has never been tested at this scale.`,
    source: 'Ars Technica', url: '#', image_url: null,
    published_at: new Date(Date.now() - 18 * 3600000).toISOString(),
    category: 'Science', ai_slop_score: 0.44,
  },
  {
    id: 'art008',
    title: 'Ultra-Processed Diet Linked to 28% Faster Cognitive Decline Over 15 Years',
    content: `A longitudinal study tracking 11,000 adults over 15 years found that high consumption of ultra-processed foods correlates with a 28% faster rate of cognitive decline, independent of total caloric intake, cardiovascular risk factors, and socioeconomic status.\n\nThe research, a joint effort between UCL and Harvard T.H. Chan School of Public Health and published in Nature Aging, points to food additive combinations — rather than any single ingredient — as the probable driver of neuroinflammatory pathways associated with early-onset dementia. The effect was most pronounced in participants consuming more than four servings of ultra-processed food per day.`,
    source: 'The Guardian', url: '#', image_url: null,
    published_at: new Date(Date.now() - 24 * 3600000).toISOString(),
    category: 'Health', ai_slop_score: 0.38,
  },
];

export const MOCK_FACTCHECK = {
  evaluations: [
    {
      claim: 'GPT-5 demonstrates a 43% improvement on MATH benchmark over GPT-4',
      verdict: 'supported',
      confidence: 0.84,
      evidence: 'Multiple independent benchmark leaderboards and OpenAI\'s published technical report corroborate this improvement across 12 evaluation datasets, including MATH, GSM8K, and AIME.',
    },
    {
      claim: 'The deployment raises questions about emergent deceptive alignment',
      verdict: 'supported',
      confidence: 0.78,
      evidence: 'Published AI safety literature from Anthropic, DeepMind, and academic institutions widely documents deceptive alignment as an open concern; the claim accurately represents current scientific discourse.',
    },
    {
      claim: 'GPT-5 achieves near-perfect coding accuracy on HumanEval',
      verdict: 'contradicted',
      confidence: 0.71,
      evidence: 'Available HumanEval benchmarks show scores in the 78-85% range for frontier models. "Near-perfect" overstates the improvement. The hardest problems remain largely unsolved.',
    },
    {
      claim: 'The model is available to approximately 400 enterprise accounts',
      verdict: 'not-mentioned',
      confidence: 0.52,
      evidence: 'No corroborating source was found in the knowledge base for this specific figure. The claim cannot be independently verified or denied from available evidence.',
    },
  ],
};

export const MOCK_CLUSTERS = {
  article_id: 'art001',
  topic_query: 'GPT-5 AI capabilities reasoning',
  pillar_count: 3,
  noise_article_count: 5,
  pillars: [
    {
      cluster_id: 0,
      summary: 'Mainstream technology media frames GPT-5 as a decisive milestone in the AI capability race, focusing on benchmark improvements and OpenAI\'s competitive repositioning against Google DeepMind and Anthropic.',
      article_count: 14,
      representative_urls: ['#', '#'],
      divergence_score: 0.31,
    },
    {
      cluster_id: 1,
      summary: 'AI safety researchers argue that capability improvements without commensurate alignment research create novel, potentially undetectable failure modes — particularly in self-verifying systems that can mask errors with false confidence.',
      article_count: 7,
      representative_urls: ['#'],
      divergence_score: 0.74,
    },
    {
      cluster_id: 2,
      summary: 'Labour economists examine whether reasoning-capable AI accelerates white-collar automation timelines, with particular focus on legal research, financial analysis, and scientific literature review roles.',
      article_count: 9,
      representative_urls: ['#', '#'],
      divergence_score: 0.51,
    },
  ],
};

export const MOCK_LEADERBOARD = [
  { user_id: 'epistemic_eagle',  total_score: 94.7 },
  { user_id: 'demo_user',        total_score: 87.3 },
  { user_id: 'critical_mind_x',  total_score: 82.1 },
  { user_id: 'news_skeptic_99',  total_score: 76.8 },
  { user_id: 'verity_seeker',    total_score: 71.2 },
  { user_id: 'factual_fred',     total_score: 65.9 },
  { user_id: 'data_journalist',  total_score: 61.4 },
  { user_id: 'the_contrarian',   total_score: 58.0 },
  { user_id: 'balanced_reader',  total_score: 52.7 },
  { user_id: 'casual_browser',   total_score: 41.3 },
];

export const MOCK_PNC = {
  user_id: USER_ID,
  epistemic_framework: { primary_mode: 'empiricist', verification_threshold: 0.78 },
  narrative_preferences: { diversity_weight: 0.65, bias_tolerance: 'low' },
  topical_constraints: {
    priority_domains: ['technology', 'AI', 'science', 'policy'],
    excluded_topics: ['celebrity gossip', 'sports'],
  },
  complexity_preference: { readability_depth: 'expert', data_density: 'high' },
};

/* ════════════════════════════════
   API FUNCTIONS
════════════════════════════════ */

export async function getFeed() {
  try {
    const { data } = await client.get('/feed');
    return data;
  } catch {
    return MOCK_ARTICLES;
  }
}

export async function getPersonalizedFeed() {
  try {
    const { data } = await client.get(`/personalized_feed/${USER_ID}`);
    return data;
  } catch {
    return MOCK_ARTICLES;
  }
}

export async function getArticle(id) {
  try {
    const { data } = await client.get(`/article/${id}`);
    return data;
  } catch {
    return MOCK_ARTICLES.find(a => a.id === id) || MOCK_ARTICLES[0];
  }
}

export async function factCheckArticle(id) {
  try {
    const { data } = await client.post(`/article/${id}/fact-check`);
    return data;
  } catch {
    return MOCK_FACTCHECK;
  }
}

export async function factCheckText(text) {
  try {
    const { data } = await client.post('/fact-check', { text });
    return data;
  } catch {
    return MOCK_FACTCHECK;
  }
}

export async function getClusters(id) {
  try {
    const { data } = await client.get(`/article/${id}/clusters`);
    return data;
  } catch {
    return MOCK_CLUSTERS;
  }
}

export async function generatePNC(naturalLanguage) {
  try {
    const { data } = await client.post('/pnc/generate', {
      natural_language: naturalLanguage,
      user_id: USER_ID,
    });
    return data;
  } catch {
    return MOCK_PNC;
  }
}

export async function getPNC() {
  try {
    const { data } = await client.get(`/pnc/${USER_ID}`);
    return data;
  } catch {
    return MOCK_PNC;
  }
}

export async function savePNC(pncData) {
  try {
    const { data } = await client.post(`/pnc/${USER_ID}`, pncData);
    return data;
  } catch {
    return pncData;
  }
}

export async function getLeaderboard(limit = 10) {
  try {
    const { data } = await client.get(`/leaderboard/top?limit=${limit}`);
    return data;
  } catch {
    return MOCK_LEADERBOARD;
  }
}

export async function recordEvent(articleId, timeSpentSecs) {
  try {
    const { data } = await client.post('/leaderboard/event', {
      user_id: USER_ID,
      article_id: articleId,
      time_spent_secs: timeSpentSecs,
    });
    return data;
  } catch {
    return null;
  }
}
