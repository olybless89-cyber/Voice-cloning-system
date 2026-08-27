import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, mediaUrl } from '../api/client';
import AudioPlayer from '../components/AudioPlayer';
import ScriptStudio from '../components/ScriptStudio';
import { useToast } from '../context/ToastContext';
import type { Generation, TreeItem } from '../types';

const SAMPLE = 'Welcome to our platform. This is an example of AI-generated speech.';

type Pickable = TreeItem;

function groupVoices(voices: Pickable[]) {
  return {
    public: voices.filter((v) => v.status === 'public'),
    private: voices.filter((v) => v.status === 'private'),
  };
}

export default function TTS() {
  const [params] = useSearchParams();
  const [voices, setVoices] = useState<Pickable[]>([]);
  const [voiceId, setVoiceId] = useState<number | ''>('');
  const [text, setText] = useState('');
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<Generation | null>(null);
  const [error, setError] = useState('');
  const { toast } = useToast();

  const grouped = useMemo(() => groupVoices(voices), [voices]);

  const usingVoices = useMemo(
    () => voices.filter((v) => v.status === 'public' || v.status === 'private'),
    [voices]
  );

  useEffect(() => {
    api
      .tree()
      .then((tree) => {
        const all = [...tree.library, ...tree.mine];
        setVoices(all);
        const usable = all.filter(
          (v) => v.status === 'public' || v.status === 'private'
        );
        const param = Number(params.get('voice'));
        if (param && usable.some((v) => v.id === param)) {
          setVoiceId(param);
        } else if (usable.length) {
          setVoiceId((prev) => prev || usable[0].id);
        }
      })
      .catch((e) => setError(e?.response?.data?.detail || 'Failed to load voices'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const generate = async () => {
    if (!voiceId) {
      setError('Please select a voice.');
      return;
    }
    if (!text.trim()) {
      setError('Please enter some text to generate.');
      return;
    }
    setError('');
    setGenerating(true);
    setResult(null);
    try {
      const gen = await api.generate(Number(voiceId), text.trim());
      setResult(gen);
      toast('Audio generated', 'success');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Generation failed. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const download = () => {
    if (!result) return;
    const a = document.createElement('a');
    a.href = mediaUrl(result.audio_url);
    a.download = '';
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Text to Speech</h1>
          <p>Choose a voice → enter text → generate audio. Simple as that.</p>
        </div>
      </div>

      <div className="panel">
        <div className="field">
          <label>1. Select a voice</label>
          <select value={voiceId} onChange={(e) => { setVoiceId(e.target.value ? Number(e.target.value) : ''); setResult(null); }}>
            <option value="">— Select a voice —</option>
            {usingVoices.length === 0 && <option value="" disabled>No voices available yet</option>}
            {grouped.public.length > 0 && (
              <optgroup label="Voice Library">
                {grouped.public.map((v) => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </optgroup>
            )}
            {grouped.private.length > 0 && (
              <optgroup label="My Voices">
                {grouped.private.map((v) => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </optgroup>
            )}
          </select>
        </div>

        <div className="field">
          <label>2. Enter text</label>
          <textarea
            rows={4}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={SAMPLE}
            maxLength={2000}
            disabled={generating}
          />
        </div>

        {error && <div className="error-text" style={{ marginBottom: 10 }}>{error}</div>}

        <button className="btn-primary" onClick={() => void generate()} disabled={generating}>
          {generating ? 'Generating speech…' : 'Generate Audio'}
        </button>
      </div>

      <ScriptStudio text={text} onApply={(t) => { setText(t); setResult(null); }} />

      {generating && (
        <div className="panel flex-row">
          <div className="spinner" />
          <p>Generating realistic speech with the selected voice…</p>
        </div>
      )}

      {result && (
        <div className="panel">
          <h3>Generated audio</h3>
          <p className="hint">Voice: {result.voice_name} · {Math.round(result.duration_seconds || 0)}s</p>
          <AudioPlayer src={result.audio_url} autoPlay />
          <div style={{ marginTop: 12 }}>
            <button className="btn-outline btn-sm" onClick={download}>⬇ Download audio</button>
          </div>
          <button
            className="btn-ghost btn-sm"
            style={{ marginTop: 8 }}
            onClick={() => { setResult(null); setText(''); }}
          >
            Generate another
          </button>
        </div>
      )}
    </div>
  );
}