import { useState } from 'react';
import { api, type CheckinResult } from '../api';

const MODES = [
  { key: 'focus', icon: '\ud83c\udfaf', label: '\u0424\u043e\u043a\u0443\u0441' },
  { key: 'support', icon: '\ud83d\udc9b', label: '\u041f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0430' },
  { key: 'coach', icon: '\ud83d\ude80', label: '\u041a\u043e\u0443\u0447' },
  { key: 'reflection', icon: '\ud83e\ude9e', label: '\u0420\u0435\u0444\u043b\u0435\u043a\u0441\u0438\u044f' },
];

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
        <div className="text-2xl mb-2">\u2705</div>
        <p className="text-[var(--tg-text)]">\u0422\u044b \u0443\u0436\u0435 \u0441\u0434\u0435\u043b\u0430\u043b check-in \u0441\u0435\u0433\u043e\u0434\u043d\u044f!</p>
      </div>
    );
  }

  if (result) {
    return (
      <div className="card p-4 space-y-3">
        <div className="text-center">
          <div className="text-2xl mb-1">\ud83c\udf89</div>
          <p className="font-bold text-[var(--tg-text)]">Check-in \u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d!</p>
        </div>
        <div className="flex justify-center gap-4 text-sm">
          <span>\ud83d\udd25 Streak: {result.streak}</span>
          <span>\ud83c\udfc5 XP: {result.xp}</span>
          <span>{result.level.icon} {result.level.name}</span>
        </div>
        {result.new_achievements.length > 0 && (
          <div className="space-y-1">
            {result.new_achievements.map(a => (
              <div key={a.code} className="text-center text-sm">
                \ud83c\udfc5 {a.icon} <strong>{a.name}</strong> +{a.xp_reward} XP
              </div>
            ))}
          </div>
        )}
        <button
          onClick={onComplete}
          className="w-full py-2 rounded-xl bg-[var(--tg-button)] text-[var(--tg-button-text)] font-medium"
        >
          \u0413\u043e\u0442\u043e\u0432\u043e
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
      const msg = e instanceof Error ? e.message : '\u041e\u0448\u0438\u0431\u043a\u0430';
      if (msg === 'already_checked_in') {
        setError('\u0422\u044b \u0443\u0436\u0435 \u0441\u0434\u0435\u043b\u0430\u043b check-in \u0441\u0435\u0433\u043e\u0434\u043d\u044f');
      } else {
        setError('\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439 \u043f\u043e\u0437\u0436\u0435.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-4 space-y-4">
      <h2 className="font-bold text-lg text-[var(--tg-text)]">\u2705 Check-in</h2>

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
        placeholder={'\u041a\u0430\u043a \u043f\u0440\u043e\u0448\u0451\u043b \u0442\u0432\u043e\u0439 \u0434\u0435\u043d\u044c? \u0427\u0442\u043e \u0441\u0434\u0435\u043b\u0430\u043b, \u0447\u0442\u043e \u043f\u043e\u043d\u044f\u043b, \u0447\u0442\u043e \u043f\u043b\u0430\u043d\u0438\u0440\u0443\u0435\u0448\u044c?'}
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
        {loading ? '\u23f3 \u0410\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u044e...' : '\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c'}
      </button>
    </div>
  );
}
