import { useEffect, useState, useCallback } from 'react';
import { api, type Profile, type AchievementsData, type Goal } from './api';
import { ProfileCard } from './components/ProfileCard';
import { ActivityCalendar } from './components/ActivityCalendar';
import { Achievements } from './components/Achievements';
import { GoalsList } from './components/GoalsList';
import { CheckinForm } from './components/CheckinForm';

export default function App() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [achievements, setAchievements] = useState<AchievementsData | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [activity, setActivity] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    window.Telegram?.WebApp?.ready();
    window.Telegram?.WebApp?.expand();

    loadData();
  }, []);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      api.profile(),
      api.achievements(),
      api.goals(),
      api.activity(),
    ])
      .then(([p, a, g, act]) => {
        setProfile(p);
        setAchievements(a);
        setGoals(g.goals);
        setActivity(act.activity);
      })
      .catch(() => setError('Не удалось загрузить данные'))
      .finally(() => setLoading(false));
  };

  const isCheckedInToday = useCallback(() => {
    if (!profile?.last_checkin_date) return false;
    const today = new Date().toISOString().slice(0, 10);
    return profile.last_checkin_date === today;
  }, [profile]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-dvh">
        <div className="text-2xl animate-pulse">⏳</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-dvh text-[var(--tg-hint)] p-4">
        {error}
      </div>
    );
  }

  return (
    <div className="p-4 pb-8 space-y-4 max-w-lg mx-auto">
      {profile && <ProfileCard profile={profile} />}
      {profile && (
        <CheckinForm
          defaultMode={profile.ai_mode}
          alreadyCheckedIn={isCheckedInToday()}
          onComplete={loadData}
        />
      )}
      <ActivityCalendar activity={activity} />
      {achievements && <Achievements data={achievements} />}
      {goals.length > 0 && <GoalsList goals={goals} />}
    </div>
  );
}
