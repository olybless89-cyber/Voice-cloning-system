import { useEffect, useState } from 'react';
import { api, type HealthReport } from '../api/client';

/**
 * Friendly "voice engine not configured yet" banner. Pings /api/health;
 * when the backend reports `ready: false` (missing Postgres / JWT secret /
 * ElevenLabs key) we show a short, human-readable setup notice instead of
 * letting users hit raw API errors. Auto-hides once the backend is ready.
 */
export default function ReadinessBanner() {
  const [report, setReport] = useState<HealthReport | null>(null);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .health()
      .then((r) => {
        if (cancelled) return;
        setReport(r);
        if (r.ready) setHidden(true);
      })
      .catch(() => {
        if (cancelled) return;
        setReport({ status: 'error', ready: false });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (hidden || !report || report.ready) return null;

  const isHardError = report.status === 'error';
  const title = isHardError
    ? 'The voice engine is unreachable right now.'
    : 'Voxcraft is almost ready for audio — a few things need configuring.';

  return (
    <div className="readiness-banner" role="alert">
      <div className="readiness-icon" aria-hidden="true">
        {isHardError ? '⚠️' : '🛠️'}
      </div>
      <div className="readiness-body">
        <strong>{title}</strong>
        <p>
          {isHardError
            ? 'The app builds and the frontend loads, but the audio backend could not be reached. Check that the deployed backend is healthy.'
            : 'Your site is live, but speech generation and voice cloning are disabled until these are set on Railway (Variables):'}
        </p>
        {!isHardError && report.warnings && (
          <ul>
            {report.warnings.map((w) => (
              <li key={w}>{friendlyWarning(w)}</li>
            ))}
          </ul>
        )}
        <p className="readiness-fineprint">
          Every other feature (accounts, exploring the voice library) works today.
          Audio generation will turn on automatically the moment the keys are added.
        </p>
      </div>
      <button
        className="btn-ghost btn-sm"
        onClick={() => setHidden(true)}
        aria-label="Dismiss notice"
      >
        Dismiss
      </button>
    </div>
  );
}

function friendlyWarning(raw: string): string {
  if (/DATABASE_URL/.test(raw))
    return 'Connect a Postgres database (DATABASE_URL) — required for production.';
  if (/JWT_SECRET/.test(raw))
    return 'Set a strong JWT_SECRET (any long random string).';
  if (/ELEVENLABS_API_KEY/.test(raw))
    return 'Add your ELEVENLABS_API_KEY — this powers all voice generation.';
  if (/ELEVENLABS/.test(raw)) return 'The ElevenLabs voice API could not be reached.';
  return raw;
}