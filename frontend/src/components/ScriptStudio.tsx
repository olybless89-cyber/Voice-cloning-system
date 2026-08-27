import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { useToast } from '../context/ToastContext';

const TONES = ['natural', 'warm', 'energetic', 'professional', 'friendly', 'dramatic'];
const LANGUAGES = [
  'English', 'Spanish', 'French', 'German', 'Italian', 'Portuguese',
  'Dutch', 'Polish', 'Turkish', 'Hindi', 'Chinese', 'Japanese',
];

interface Props {
  text: string;
  onApply: (text: string) => void;
}

export default function ScriptStudio({ text, onApply }: Props) {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [tone, setTone] = useState(TONES[0]);
  const [lang, setLang] = useState(LANGUAGES[0]);
  const [result, setResult] = useState('');
  const { toast } = useToast();
  const textRef = useRef(text);
  textRef.current = text;

  useEffect(() => {
    // Non-fatal: if the agent is off, the panel just hides its buttons.
    api.agentStatus().then((s) => setEnabled(s.enabled)).catch(() => setEnabled(false));
  }, []);

  const run = async (kind: 'rewrite' | 'proofread' | 'translate' | 'summarise') => {
    if (!textRef.current.trim()) {
      toast('Enter some text first', 'info');
      return;
    }
    setBusy(kind);
    setResult('');
    try {
      const out =
        kind === 'rewrite'
          ? await api.agentRewrite(textRef.current, tone)
          : kind === 'proofread'
            ? await api.agentProofread(textRef.current)
            : kind === 'translate'
              ? await api.agentTranslate(textRef.current, lang)
              : await api.agentSummarise(textRef.current, 3);
      setResult(out.text);
    } catch (e: any) {
      if (e?.response?.status === 503) {
        setEnabled(false);
        toast('Script Studio is not configured on the server', 'error');
      } else {
        toast(e?.response?.data?.detail || 'Script Studio failed', 'error');
      }
    } finally {
      setBusy(null);
    }
  };

  const apply = () => {
    if (!result.trim()) return;
    onApply(result.trim());
    setResult('');
    toast('Applied to your script', 'success');
  };

  if (enabled === false) return null;

  return (
    <div className="panel" style={{ marginTop: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <h3 style={{ margin: 0 }}>✨ Script Studio <span className="badge">AI</span></h3>
          <p className="hint" style={{ margin: '4px 0 0' }}>
            Improve your text before it becomes speech — powered by OpenAI.
          </p>
        </div>
        {enabled && <span className="hint" style={{ fontSize: 12 }}>connected</span>}
      </div>

      <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <select className="mini-select" value={tone} onChange={(e) => setTone(e.target.value)}>
          {TONES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <button className="btn-ghost btn-sm" disabled={!!busy} onClick={() => void run('rewrite')}>
          {busy === 'rewrite' ? '…' : 'Rewrite'}
        </button>
        <button className="btn-ghost btn-sm" disabled={!!busy} onClick={() => void run('proofread')}>
          {busy === 'proofread' ? '…' : 'Proofread'}
        </button>
        <select className="mini-select" value={lang} onChange={(e) => setLang(e.target.value)}>
          {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <button className="btn-ghost btn-sm" disabled={!!busy} onClick={() => void run('translate')}>
          {busy === 'translate' ? '…' : 'Translate'}
        </button>
        <button className="btn-ghost btn-sm" disabled={!!busy} onClick={() => void run('summarise')}>
          {busy === 'summarise' ? '…' : 'Summarise'}
        </button>
      </div>

      {busy && <p className="hint" style={{ marginTop: 10 }}>OpenAI is writing…</p>}

      {result && !busy && (
        <div className="script-result" style={{ marginTop: 12 }}>
          <textarea
            rows={4}
            value={result}
            onChange={(e) => setResult(e.target.value)}
            className="script-result-text"
          />
          <div style={{ marginTop: 8 }}>
            <button className="btn-primary btn-sm" onClick={apply}>Use this text</button>
            <button className="btn-ghost btn-sm" style={{ marginLeft: 8 }} onClick={() => setResult('')}>
              Discard
            </button>
          </div>
        </div>
      )}
    </div>
  );
}