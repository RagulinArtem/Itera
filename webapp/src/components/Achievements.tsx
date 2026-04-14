import type { AchievementsData } from '../api';

export function Achievements({ data }: { data: AchievementsData }) {
  return (
    <div className="rounded-2xl p-5 bg-[var(--tg-section-bg)]">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-semibold">Ачивки</h3>
        <span className="text-xs text-[var(--tg-hint)]">{data.unlocked}/{data.total}</span>
      </div>

      {data.categories.map(cat => (
        <div key={cat.category} className="mb-4 last:mb-0">
          <div className="text-xs text-[var(--tg-hint)] mb-2 text-left">{cat.category}</div>
          <div className="flex flex-wrap gap-2">
            {cat.achievements.map(a => (
              <div
                key={a.code}
                title={`${a.name}: ${a.description}${a.xp_reward ? ` (+${a.xp_reward} XP)` : ''}`}
                className={`
                  w-10 h-10 rounded-xl flex items-center justify-center text-lg
                  ${a.unlocked
                    ? 'bg-[var(--tg-btn)]/20'
                    : 'bg-black/10 opacity-30 grayscale'}
                `}
              >
                {a.unlocked ? a.icon : '🔒'}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
