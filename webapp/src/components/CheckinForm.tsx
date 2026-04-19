import { useState } from 'react';
import { api, type CheckinResult } from '../api';

const MODES = [
  { key: 'focus', icon: '🎯', label: 'Фокус' },
  { key: 'support', icon: '💛', label: 'Поддержка' },
  { key: 'coach', icon: '🚀', label: 'Коуч' },
  { key: 'reflection', icon: '🪞', label: 'Рефлексия' },
];

function extractAIText(analysis: Record<string, unknown>): string {
  // Try telegram.text_markdown first (support/coach/reflection modes)
  const tg = analysis.telegram as Record<string, unknown> | undefined;
  if (tg?.text_markdown) return String(tg.text_markdown);

  // Focus mode: build from fields
  const parts: string[] = [];
  const verdict = analysis.verdict as Record<string, string> | undefined;
  if (verdict?.reason) parts.push(verdict.reason);
  const conclusion = analysis.day_conclusion;
  if (conclusion) parts.push(String(conclusion));
  const insights = analysis.insights as string[] | undefined;
  if (insights?.length) parts.push(insights.join('\n'));

  // Fallback: response fields (coach/reflection/support)
  const resp = analysis.response as Record<string, unknown> | undefined;
  if (resp) {
    for (const key of ['mirror', 'honest_mirror', 'echo', 'reframe', 'question', 'power_question']) {
      if (resp[key]) parts.push(String(resp[key]));
    }
  }

  return parts.join('\n\n') || 'Анализ сохранён';
}

interface Props {
  defaultMode: string;
  alreadyCheckedIn: boolean;
  onComplete: () => void;
}

export function CheckinForm({ defaultMode, alreadyCheckedIn, onComplete }: Props) {
  const [text, setText] = useState('');
  const [mode, setMode] = useState(defaultMode);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CheckinResult | null>(null);
  const [error, setError] = useState('');

  if (alreadyCheckedIn && !result) {
    return (
      <div className="card p-4 text-center">
        <div className="text-2xl mb-2">✅</div>
        <p className="text-[var(--tg-text)]">Ты уже сделал check-in сегодня!</p>
      </div>
    );
  }

  if (result) {
    const aiText = extractAIText(result.analysis);
    return (
      <div className="card p-4 space-y-3">
        <div className="text-center">
          <div className="text-2xl mb-1">🎉</div>
          <p className="font-bold text-[var(--tg-text)]">Check-in сохранён!</p>
        </div>
        <div className="flex justify-center gap-4 text-sm">
          <span>🔥 Streak: {result.streak}</span>
          <span>🏅 XP: {result.xp}</span>
          <span>{result.level.icon} {result.level.name}</span>
        </div>
        {result.new_achievements.length > 0 && (
          <div className="space-y-1">
            {result.new_achievements.map(a => (
              <div key={a.code} className="text-center text-sm">
                🏅 {a.icon} <strong>{a.name}</strong> +{a.xp_reward} XP
              </div>
            ))}
          </div>
        )}
        {/* AI analysis text */}
        <div className="bg-[var(--tg-secondary-bg)] rounded-xl p-3 text-sm text-[var(--tg-text)] whitespace-pre-wrap leading-relaxed">
          {aiText}
        </div>
        <button
          onClick={onComplete}
          className="w-full py-2 rounded-xl bg-[var(--tg-button)] text-[var(--tg-button-text)] font-medium"
        >
          Готово
        </button>
      </div>
    );
  }

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await api.submitCheckin(text.trim(), mode);
      setResult(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Ошибка';
      if (msg === 'already_checked_in') {
        setError('Ты уже сделал check-in сегодня');
      } else {
        setError('Не удалось отправить. Попробуй позже.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-4 space-y-4">
      <h2 className="font-bold text-lg text-[var(--tg-text)]">✅ Check-in</h2>

      {/* Mode selector */}
      <div className="flex gap-2">
        {MODES.map(m => (
          <button
            key={m.key}
            onClick={() => setMode(m.key)}
            className={`flex-1 py-2 rounded-xl text-xs font-medium transition-all ${
              mode === m.key
                ? 'bg-[var(--tg-button)] text-[var(--tg-button-text)] shadow-sm'
                : 'bg-[var(--tg-secondary-bg)] text-[var(--tg-hint)]'
            }`}
          >
            {m.icon} {m.label}
          </button>
        ))}
      </div>

      {/* Text input */}
      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="Как прошёл твой день? Что сделал, что понял, что планируешь?"
        rows={5}
        className="w-full p-3 rounded-xl bg-[var(--tg-secondary-bg)] text-[var(--tg-text)] placeholder-[var(--tg-hint)] resize-none outline-none border-none text-sm"
        disabled={loading}
      />

      {error && <p className="text-red-400 text-sm text-center">{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={loading || !text.trim()}
        className="w-full py-3 rounded-xl bg-[var(--tg-button)] text-[var(--tg-button-text)] font-medium disabled:opacity-50 transition-opacity"
      >
        {loading ? '⏳ Анализирую...' : 'Отправить'}
      </button>
    </div>
  );
}
