const BASE = '/api';

function getInitData(): string {
  return window.Telegram?.WebApp?.initData || '';
}

async function request<T>(path: string, query?: Record<string, string>): Promise<T> {
  const url = new URL(path, window.location.origin);
  if (query) {
    for (const [k, v] of Object.entries(query)) url.searchParams.set(k, v);
  }
  const res = await fetch(url.toString(), {
    headers: { Authorization: `tma ${getInitData()}` },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export interface LevelInfo {
  number: number;
  name: string;
  icon: string;
  min_xp: number;
}

export interface Profile {
  nickname: string;
  xp: number;
  streak: number;
  ai_mode: string;
  last_checkin_date: string | null;
  level: LevelInfo;
  next_level: LevelInfo | null;
}

export interface Achievement {
  code: string;
  icon: string;
  name: string;
  description: string;
  xp_reward: number;
  unlocked: boolean;
}

export interface AchievementCategory {
  category: string;
  achievements: Achievement[];
}

export interface AchievementsData {
  total: number;
  unlocked: number;
  categories: AchievementCategory[];
}

export interface Goal {
  id: string;
  goal: string;
  status: string;
  progress: number;
  plan: Record<string, unknown>;
  created_at: string;
  completed_at: string | null;
}

export interface CheckinResult {
  ok: boolean;
  analysis: Record<string, unknown>;
  streak: number;
  xp: number;
  level: { number: number; name: string; icon: string };
  new_achievements: Array<{ code: string; icon: string; name: string; xp_reward: number }>;
}

async function postRequest<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: {
      Authorization: `tma ${getInitData()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `API ${res.status}`);
  }
  return res.json();
}

export const api = {
  profile: () => request<Profile>(`${BASE}/profile`),
  achievements: () => request<AchievementsData>(`${BASE}/achievements`),
  goals: () => request<{ goals: Goal[] }>(`${BASE}/goals`),
  activity: () => request<{ activity: Record<string, number> }>(`${BASE}/activity`),
  checkins: (limit = 30) => request<{ checkins: Array<{ date: string; text: string; analysis: unknown; created_at: string }> }>(`${BASE}/checkins`, { limit: String(limit) }),
  submitCheckin: (text: string, mode?: string) => postRequest<CheckinResult>('/checkin', { text, mode }),
};
