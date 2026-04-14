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

export const api = {
  profile: () => request<Profile>(`${BASE}/profile`),
  achievements: () => request<AchievementsData>(`${BASE}/achievements`),
  goals: () => request<{ goals: Goal[] }>(`${BASE}/goals`),
  activity: () => request<{ activity: Record<string, number> }>(`${BASE}/activity`),
  checkins: (limit = 30) => request<{ checkins: Array<{ date: string; text: string; analysis: unknown; created_at: string }> }>(`${BASE}/checkins`, { limit: String(limit) }),
};
