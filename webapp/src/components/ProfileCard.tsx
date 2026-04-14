import type { Profile } from '../api';

export function ProfileCard({ profile }: { profile: Profile }) {
  const { level, next_level, xp, streak } = profile;

  const progress = next_level
    ? ((xp - level.min_xp) / (next_level.min_xp - level.min_xp)) * 100
    : 100;

  return (
    <div className="rounded-2xl p-5 bg-[var(--tg-section-bg)]">
      <div className="flex items-center gap-3 mb-4">
        <span className="text-4xl">{level.icon}</span>
        <div className="text-left">
          <div className="text-lg font-semibold">{profile.nickname || 'Пользователь'}</div>
          <div className="text-sm text-[var(--tg-hint)]">
            {level.name} · Уровень {level.number}
          </div>
        </div>
      </div>

      {/* XP bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-[var(--tg-hint)] mb-1">
          <span>{xp} XP</span>
          <span>{next_level ? `${next_level.min_xp} XP` : 'MAX'}</span>
        </div>
        <div className="h-2.5 rounded-full bg-black/20 overflow-hidden">
          <div
            className="h-full rounded-full bg-[var(--tg-btn)] transition-all duration-500"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
        {next_level && (
          <div className="text-xs text-[var(--tg-hint)] mt-1">
            {next_level.min_xp - xp} XP до {next_level.icon} {next_level.name}
          </div>
        )}
      </div>

      {/* Stats row */}
      <div className="flex gap-3">
        <StatBadge icon="🔥" value={streak} label="streak" />
        <StatBadge icon="⚡" value={xp} label="XP" />
      </div>
    </div>
  );
}

function StatBadge({ icon, value, label }: { icon: string; value: number; label: string }) {
  return (
    <div className="flex-1 rounded-xl py-2 px-3 bg-black/10 text-center">
      <div className="text-lg font-bold">{icon} {value}</div>
      <div className="text-xs text-[var(--tg-hint)]">{label}</div>
    </div>
  );
}
