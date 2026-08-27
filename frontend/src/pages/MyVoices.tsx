import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import VoiceCard from '../components/VoiceCard';
import { useToast } from '../context/ToastContext';
import type { Voice } from '../types';

type Stage = 'idle' | 'uploading' | 'processing' | 'naming' | 'failed';

const FLOW_STEPS = [
  { label: 'Uploading', state: 'uploading' },
  { label: 'Processing', state: 'processing' },
  { label: 'Creating Voice', state: 'naming' },
];

export default function MyVoices() {
  const [voices, setVoices] = useState<Voice[] | null>(null);
  const [error, setError] = useState('');
  const [stage, setStage] = useState<Stage>('idle');
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [fileName, setFileName] = useState('');
  const [dragging, setDragging] = useState(false);
  const [cloneName, setCloneName] = useState('');
  const navigate = useNavigate();
  const { toast } = useToast();
  const inputRef = useRef<HTMLInputElement>(null);

  const load = () => {
    api
      .mine()
      .then(setVoices)
      .catch((e) => setError(e?.response?.data?.detail || 'Failed to load voices'));
  };

  useEffect(load, []);

  const clone = async (file: File) => {
    setFileName(file.name);
    setError('');
    setStage('uploading');
    try {
      const res = await api.uploadClone(file);
      setPendingId(res.id);
      setStage('processing');
      // Simulated AI processing delay so the user sees the state clearly.
      await new Promise((r) => setTimeout(r, 1500));
      setStage('naming');
    } catch (e: any) {
      setStage('failed');
      setError(e?.response?.data?.detail || 'Cloning failed. Please try again.');
    }
  };

  const saveName = async () => {
    if (!cloneName.trim() || pendingId == null) return;
    setError('');
    try {
      await api.finalizeClone(pendingId, cloneName.trim());
      toast('Voice created and ready to use', 'success');
      setStage('idle');
      setPendingId(null);
      setCloneName('');
      setFileName('');
      load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create voice.');
    }
  };

  const deleteVoice = async (id: number) => {
    if (!window.confirm('Delete this voice? This cannot be undone.')) return;
    try {
      await api.deleteVoice(id);
      toast('Voice deleted', 'success');
      load();
    } catch (e: any) {
      toast(e?.response?.data?.detail || 'Failed to delete voice', 'error');
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void clone(file);
  };

  const stepIndex = ['uploading', 'processing', 'naming'].indexOf(stage);
  const failed = stage === 'failed';

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>My Voices</h1>
          <p>Clone your own voice with a ~1 minute audio sample.</p>
        </div>
        <button className="btn-outline btn-sm" onClick={() => load()}>Refresh</button>
      </div>

      {/* Clone flow */}
      <div className="panel">
        <h3>Clone a voice</h3>
        <p style={{ marginBottom: 14 }}>
          Upload roughly 1 minute of clear speech from any speaker to create a custom voice.
        </p>

        {(stage === 'idle' || stage === 'failed') && (
          <div
            className={`drag-zone ${dragging ? 'dragging' : ''}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <div style={{ fontSize: 30 }}>{failed ? '❗' : '🎤'}</div>
            <div style={{ fontWeight: 600, marginTop: 6 }}>
              {failed ? 'Cloning failed — try again' : 'Click or drop an audio file here'}
            </div>
            {failed && error && <div className="error-text" style={{ maxWidth: 420, margin: '8px auto' }}>{error}</div>}
            <div className="tip">{fileName || 'Accepted: MP3, WAV, M4A, OGG · ~1 minute'}</div>
            <input
              ref={inputRef}
              type="file"
              accept="audio/*"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void clone(f);
                e.target.value = '';
              }}
            />
          </div>
        )}

        {(stage === 'uploading' || stage === 'processing') && (
          <div>
            <div className="stepper">
              {FLOW_STEPS.map((s, i) => (
                <span key={s.state} className={`step ${i <= stepIndex ? (i < stepIndex ? 'done' : 'active') : ''}`}>
                  <span className="dot" /> {s.label}
                  {i < FLOW_STEPS.length - 1 && <span className="sep">→</span>}
                </span>
              ))}
            </div>
            <div className="flex-row">
              <div className="spinner" />
              <p>{stage === 'uploading' ? `Uploading ${fileName}…` : 'Processing your voice sample…'}</p>
            </div>
          </div>
        )}

        {stage === 'naming' && (
          <div>
            <div className="stepper">
              {FLOW_STEPS.map((s, i) => (
                <span key={s.state} className="step done">
                  <span className="dot" /> {s.label} {i < FLOW_STEPS.length - 1 && <span className="sep">→</span>}
                </span>
              ))}
            </div>
            <div className="input-group" style={{ maxWidth: 460 }}>
              <input
                value={cloneName}
                onChange={(e) => setCloneName(e.target.value)}
                placeholder="Name this voice (e.g. John)"
                autoFocus
                onKeyDown={(e) => { if (e.key === 'Enter') void saveName(); }}
              />
              <button className="btn-primary" onClick={() => void saveName()} disabled={!cloneName.trim()}>
                Save Voice
              </button>
            </div>
            <div className="hint">Your voice is ready — give it a name to use it in Text to Speech.</div>
            {error && <div className="error-text">{error}</div>}
          </div>
        )}
      </div>

      {/* My voices list */}
      <h2 style={{ marginBottom: 12 }}>Your cloned voices</h2>
      {voices && voices.length === 0 ? (
        <div className="empty">
          <div className="big">🗣️</div>
          <p>You haven&apos;t cloned any voices yet.</p>
        </div>
      ) : (
        <div className="grid">
          {(voices ?? []).map((v) => (
            <VoiceCard
              key={v.id}
              voice={v}
              onUse={(id) => navigate(`/dashboard/tts?voice=${id}`)}
              onDelete={deleteVoice}
            />
          ))}
        </div>
      )}
    </div>
  );
}