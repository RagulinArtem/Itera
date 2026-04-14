import type { Goal } from '../api';

const STATUS = {
  active: { icon: '🟢', label: 'Active' },
  completed: { icon: '✅', label: 'Completed' },
  archived: { icon: '⏸', label: 'Archived' },
} as const;

export function GoalsList({ goals }: { goals: Goal[] }) {
  if (!goals.length) return null;

  const active = goals.filter(g => g.status === 'active');
  const done = goals.filter(g => g.status !== 'active');

  return (
    <div className="rounded-2xl p-5 bg-[var(--tg-section-bg)]">
      <h3 className="text-sm font-semibold mb-3 text-left">Цели</h3>

      {active.map(g => <GoalCard key={g.id} goal={g} />)}

      {done.length > 0 && (
        <>
          <div className="text-xs text-[var(--tg-hint)] mt-4 mb-2 text-left">Завершённые</div>
          {done.map(g => <GoalCard key={g.id} goal={g} />)}
        </>
      )}
    </div>
  );
}

function GoalCard({ goal }: { goal: Goal }) {
  const s = STATUS[goal.status as keyof typeof STATUS] || STATUS.active;
  const plan = goal.plan as { items?: Array<{ label: string }> };
  const steps = plan?.items || [];

  return (
    <div className="rounded-xl p-3 mb-2 last:mb-0 bg-black/10 text-left">
      <div className="flex items-start gap-2">
        <span>{s.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm truncate">{goal.goal}</div>
          {steps.length > 0 && (
            <div className="mt-1.5 space-y-1">
              {steps.slice(0, 3).map((step, i) => (
                <div key={i} className="text-xs text-[var(--tg-hint)] flex items-start gap-1.5">
                  <span>→</span>
                  <span>{step.label}</span>
                </div>
              ))}
              {steps.length > 3 && (
                <div className="text-xs text-[var(--tg-hint)]">+{steps.length - 3} шагов</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
