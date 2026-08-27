import { useCallback, useEffect, useState } from 'react';
import { api, mediaUrl } from '../api/client';
import { useToast } from '../context/ToastContext';
import type { Generation } from '../types';

function fmtDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export default function History() {
  const [items, setItems] = useState<Generation[] | null>(null);
  const [error, setError] = useState('');
  const { toast } = useToast();

  const load = useCallback(() => {
    api
      .history()
      .then((res) => setItems(res.items))
      .catch((e) => setError(e?.response?.data?.detail || 'Failed to load history'));
  }, []);

  useEffect(load, [load]);

  const remove = async (id: number) => {
    try {
      await api.deleteGeneration(id);
      toast('Generation deleted', 'success');
      load();
    } catch (e: any) {
      toast(e?.response?.data?.detail || 'Failed to delete', 'error');
    }
  };

  if (error) return <p className="error-text">{error}</p>;
  if (!items) return <div className="full-loader"><div className="spinner" /></div>;

  if (items.length === 0) {
    return (
      <div>
        <div className="page-head"><div><h1>Generation History</h1><p>Your previously generated audio.</p></div></div>
        <div className="empty">
          <div className="big">🕘</div>
          <p>No generations yet. Generate some audio to see it here.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Generation History</h1>
          <p>{items.length} generated audio track{items.length === 1 ? '' : 's'}.</p>
        </div>
      </div>

      <div className="panel" style={{ overflowX: 'auto' }}>
        <table>
          <thead>
            <tr>
              <th>Text</th>
              <th>Voice</th>
              <th>Created</th>
              <th>Audio</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((g) => (
              <tr key={g.id}>
                <td style={{ maxWidth: 280 }}>
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {g.text}
                  </div>
                </td>
                <td>{g.voice_name || '—'}</td>
                <td className="muted">{fmtDate(g.created_at)}</td>
                <td style={{ minWidth: 220 }}>
                  <audio controls src={mediaUrl(g.audio_url)} style={{ width: '100%', height: 36 }} />
                </td>
                <td>
                  <div className="cell-actions">
                    <a className="btn-outline btn-sm" href={mediaUrl(g.audio_url)} download>
                      ⬇
                    </a>
                    <button className="btn-danger btn-sm" onClick={() => void remove(g.id)}>
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}