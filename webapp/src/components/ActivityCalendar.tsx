import { useMemo } from 'react';

interface Props {
  activity: Record<string, number>;
}

export function ActivityCalendar({ activity }: Props) {
  const { weeks, months } = useMemo(() => {
    const today = new Date();
    const days: { date: string; count: number; dayOfWeek: number }[] = [];

    for (let i = 89; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      days.push({ date: key, count: activity[key] || 0, dayOfWeek: d.getDay() });
    }

    const w: typeof days[] = [];
    let currentWeek: typeof days = [];
    for (const day of days) {
      if (day.dayOfWeek === 1 && currentWeek.length > 0) {
        w.push(currentWeek);
        currentWeek = [];
      }
      currentWeek.push(day);
    }
    if (currentWeek.length) w.push(currentWeek);

    const m: { label: string; col: number }[] = [];
    const monthNames = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];
    let lastMonth = -1;
    w.forEach((week, wi) => {
      const d = new Date(week[0].date);
      if (d.getMonth() !== lastMonth) {
        lastMonth = d.getMonth();
        m.push({ label: monthNames[lastMonth], col: wi });
      }
    });

    return { weeks: w, months: m };
  }, [activity]);

  return (
    <div className="rounded-2xl p-5 bg-[var(--tg-section-bg)]">
      <h3 className="text-sm font-semibold mb-3 text-left">Активность (90 дней)</h3>

      <div className="flex gap-[3px] mb-1 text-[10px] text-[var(--tg-hint)]">
        {weeks.map((_, i) => {
          const month = months.find(m => m.col === i);
          return <div key={i} className="w-3 h-3 shrink-0 text-center">{month?.label || ''}</div>;
        })}
      </div>

      <div className="flex gap-[3px]">
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-[3px]">
            {week.map((day) => (
              <div
                key={day.date}
                title={`${day.date}: ${day.count} чекинов`}
                className="w-3 h-3 rounded-[2px]"
                style={{ backgroundColor: cellColor(day.count) }}
              />
            ))}
          </div>
        ))}
      </div>

      <div className="flex gap-2 mt-3 text-[10px] text-[var(--tg-hint)] items-center">
        <span>Меньше</span>
        {[0, 1, 2].map(n => (
          <div key={n} className="w-3 h-3 rounded-[2px]" style={{ backgroundColor: cellColor(n) }} />
        ))}
        <span>Больше</span>
      </div>
    </div>
  );
}

function cellColor(count: number): string {
  if (count === 0) return 'rgba(255,255,255,0.06)';
  if (count === 1) return '#2d6a4f';
  return '#52b788';
}
