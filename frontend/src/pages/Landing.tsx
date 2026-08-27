import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ReadinessBanner from '../components/ReadinessBanner';
import './landing.css';

/* ---------------------------------------------------------------
   Voxcraft — landing page.
   Editorial-premium sonic aesthetic: Fraunces display serif + Space
   Mono technical accents + Work Sans body, obsidian/teal/ember palette.
   Includes a live, working text-to-speech demo powered by the browser's
   Web Speech API so the hero actually speaks.
---------------------------------------------------------------- */

type VoiceChar = { id: string; name: string; kind: string; pitch: number; rate: number; accent: string };

const DEMO_VOICES: VoiceChar[] = [
  { id: 'aurora', name: 'Aurora', kind: 'Neural', pitch: 1.15, rate: 1.04, accent: 'var(--teal)' },
  { id: 'nolan', name: 'Nolan', kind: 'Deep', pitch: 0.8, rate: 0.95, accent: 'var(--ember)' },
  { id: 'iris', name: 'Iris', kind: 'Warm', pitch: 1.02, rate: 1.0, accent: 'var(--violet)' },
];

const LIBRARY_VOICES = [
  { name: 'Aurora', tag: 'Neural · EN-GB', mood: 'Bright, cinematic' },
  { name: 'Nolan', tag: 'Deep · EN-US', mood: 'Grounded, assured' },
  { name: 'Iris', tag: 'Warm · EN-AU', mood: 'Soft, close' },
  { name: 'Atlas', tag: 'Narrative · EN-US', mood: 'Documentary weight' },
  { name: 'Sable', tag: 'Intimate · FR', mood: 'Velvet, hushed' },
  { name: 'Kei', tag: 'Precise · EN-JP', mood: 'Crisp, editorial' },
];

const FEATURES = [
  {
    n: '01',
    t: 'Voice cloning from 60 seconds',
    d: 'Drop a single minute of clean audio. Voxcraft extracts the acoustic fingerprint and rebuilds a speaking voice that sounds like yours — nuance included.',
  },
  {
    n: '02',
    t: 'Lifelike neural text-to-speech',
    d: 'Natural prosody, emotional range and breathing. Every sentence lands the way a human editor would read it.',
  },
  {
    n: '03',
    t: 'A curated voice library',
    d: 'A living collection of public voices, preview any of them in one click and take it straight into the studio.',
  },
  {
    n: '04',
    t: 'Everything you make, archived',
    d: 'Your clones and every generation are saved to your history. Replay, download and reuse audio any time.',
  },
];

const STEPS = [
  { k: '01', t: 'Choose a voice', d: 'Browse the library or clone your own from a one-minute sample.' },
  { k: '02', t: 'Type something', d: 'Anything. A script, a snippet, a whole story.' },
  { k: '03', t: 'Generate & download', d: 'Instant lifelike audio. Play it, save it, ship it.' },
];

const STATS = [
  { v: '40+', l: 'Neural voices' },
  { v: '12', l: 'Languages' },
  { v: '60s', l: 'To clone a voice' },
  { v: '120ms', l: 'Avg. first syllable' },
];

const MARQUEE = ['Ad-lib your script', 'Clone your own voice', 'Ship narration fast', 'Broadcast-grade audio', 'Multilingual by default', 'Your archive, forever'];

export default function Landing() {
  const { user } = useAuth();
  const [cmd, setCmd] = useState(0);
  const [demoText, setDemoText] = useState('Welcome to Voxcraft. Type anything here and I will speak it back to you.');
  const [activeVoice, setActiveVoice] = useState(DEMO_VOICES[0]);
  const [speaking, setSpeaking] = useState(false);
  const [wave, setWave] = useState<number[]>(Array(40).fill(0.35));
  const synthRef = useRef<SpeechSynthesis | null>(null);

  useEffect(() => {
    const t = setInterval(() => setCmd((c) => (c + 1) % STEPS.length), 3200);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    synthRef.current = 'speechSynthesis' in window ? window.speechSynthesis : null;
    if (synthRef.current) synthRef.current.cancel();
  }, [activeVoice.id]);

  const speak = () => {
    const synth = synthRef.current;
    if (!synth) return;
    synth.cancel();
    if (speaking) {
      setSpeaking(false);
      return;
    }
    const u = new SpeechSynthesisUtterance(demoText || 'Say something first.');
    u.pitch = activeVoice.pitch;
    u.rate = activeVoice.rate;
    u.onstart = () => setSpeaking(true);
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    synth.speak(u);
    // Animate the equaliser bars while speaking
    const tick = setInterval(() => {
      setWave(Array.from({ length: 40 }, () => 0.2 + Math.random() * 0.8));
    }, 120);
    u.addEventListener('end', () => {
      clearInterval(tick);
      setWave(Array(40).fill(0.35));
    });
  };

  return (
    <div className="landing">
      {/* ---------- Grain + ambient glow ---------- */}
      <div className="grain" aria-hidden="true" />
      <div className="ambient ambient-a" aria-hidden="true" />
      <div className="ambient ambient-b" aria-hidden="true" />

      {/* ---------- Nav ---------- */}
      <header className="land-nav">
        <a className="land-brand" href="#top">
          <span className="land-logo" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          Voxcraft
        </a>
        <nav className="land-links" aria-label="Primary">
          <a href="#how">How it works</a>
          <a href="#features">Features</a>
          <a href="#voices">Voices</a>
          <a href="#faq">FAQ</a>
        </nav>
        <div className="land-cta">
          <Link to={user ? '/dashboard' : '/login'} className="lbtn ghost">
            {user ? 'Open studio' : 'Sign in'}
          </Link>
          <Link to={user ? '/dashboard' : '/register'} className="lbtn solid">
            Get started
          </Link>
        </div>
      </header>

      <main id="top">
        <div className="land-ready"><ReadinessBanner /></div>
        {/* ---------- HERO ---------- */}
        <section className="hero" style={{ marginTop: 0 }}>
          <div className="hero-inner">
            <div className="hero-copy">
              <p className="eyebrow mono">
                <span className="dot" /> AI Voice Cloning · Neural Text-to-Speech
              </p>
              <h1 className="hero-title">
                Give your words
                <br />
                <em>a voice worth</em>
                <br />
                hearing.
              </h1>
              <p className="hero-sub">
                Voxcraft turns any text into studio-clean, lifelike speech — and clones a
                voice of your own from a single one-minute sample.
              </p>
              <div className="hero-actions">
                <Link to={user ? '/dashboard' : '/register'} className="lbtn big ember">
                  Make your first voice <span aria-hidden="true">↗</span>
                </Link>
                <a className="lbtn big ghost" href="#demo">
                  <span className="playico" aria-hidden="true">▶</span> Try the live demo
                </a>
              </div>
            </div>

            {/* ---------- Live speaking demo ---------- */}
            <div className="demo" id="demo">
              <div className="demo-top mono">
                <span className="demo-label">
                  <span className="rec" aria-hidden="true" /> Studio Preview
                </span>
                <span className="demo-voice">{activeVoice.name} · {activeVoice.pitch.toFixed(2)}kHz</span>
              </div>

              <div className="wave-stage">
                <div className="wave">
                  {wave.map((h, i) => (
                    <span
                      key={i}
                      className={`bar ${speaking ? 'live' : ''}`}
                      style={{
                        transform: `scaleY(${h})`,
                        animationDelay: `${i * 30}ms`,
                        background: i < 12 ? activeVoice.accent : undefined,
                      }}
                    />
                  ))}
                </div>
              </div>

              <textarea
                className="demo-input"
                value={demoText}
                onChange={(e) => setDemoText(e.target.value)}
                rows={3}
                aria-label="Demo text to speak"
              />
              <div className="demo-voicebar">
                <div className="demo-vchoices">
                  {DEMO_VOICES.map((v) => (
                    <button
                      key={v.id}
                      className={`vchip ${activeVoice.id === v.id ? 'on' : ''}`}
                      style={activeVoice.id === v.id ? { borderColor: v.accent, color: v.accent } : undefined}
                      onClick={() => setActiveVoice(v)}
                    >
                      {v.name}
                    </button>
                  ))}
                </div>
                <button className={`speak ${speaking ? 'speaking' : ''}`} onClick={speak} disabled={!('speechSynthesis' in window)}>
                  {speaking ? '■ Stop' : '▶ Speak it'}
                </button>
              </div>
              {!('speechSynthesis' in window) && (
                <p className="demo-note">Your browser doesn't support speech — the full demo lives in the studio.</p>
              )}
            </div>
          </div>

          <div className="hero-scroll mono" aria-hidden="true">scroll → enter the studio</div>
        </section>

        {/* ---------- Stats band ---------- */}
        <section className="statsband">
          {STATS.map((s) => (
            <div className="stat" key={s.l}>
              <div className="stat-v mono">{s.v}</div>
              <div className="stat-l">{s.l}</div>
            </div>
          ))}
        </section>

        {/* ---------- Marquee ---------- */}
        <section className="marquee" aria-hidden="true">
          <div className="marquee-track">
            {[...MARQUEE, ...MARQUEE].map((m, i) => (
              <span className="mq mono" key={i}>{m}<i>✦</i></span>
            ))}
          </div>
        </section>

        {/* ---------- How it works ---------- */}
        <section className="section how" id="how">
          <div className="sec-head">
            <p className="eyebrow mono">The three-step studio</p>
            <h2 className="sec-title">
              Choose a voice.<br /><em>Type something. Done.</em>
            </h2>
            <p className="sec-sub">
              We engineered the core loop to be absurdly simple. No sliders, no settings —
              a voice, your words, and out comes audio.
            </p>
          </div>
          <div className="steps">
            {STEPS.map((s, i) => (
              <div className={`step ${cmd === i ? 'cur' : ''}`} key={s.k}>
                <div className="step-k mono">{s.k}</div>
                <div className="step-bar"><span /></div>
                <h3>{s.t}</h3>
                <p>{s.d}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ---------- Features ---------- */}
        <section className="section features" id="features">
          <div className="sec-head">
            <p className="eyebrow mono t">Engineering the sound of the future</p>
            <h2 className="sec-title">
              Not another TTS.<br /><em>An instrument.</em>
            </h2>
          </div>
          <div className="feat-grid">
            {FEATURES.map((f) => (
              <article className="feat" key={f.n}>
                <div className="feat-n mono">{f.n}</div>
                <h3>{f.t}</h3>
                <p>{f.d}</p>
              </article>
            ))}
          </div>
        </section>

        {/* ---------- Voice Lab ---------- */}
        <section className="section lab" id="lab">
          <div className="sec-head">
            <p className="eyebrow mono t">The Voice Lab</p>
            <h2 className="sec-title">
              Like a choir,<br /><em>in your pocket.</em>
            </h2>
          </div>
          <div className="lab-cards">
            <div className="lab-card">
              <div className="lab-ico" aria-hidden="true">♮</div>
              <h3>Public voice library</h3>
              <p>Preview and use a curated set of voices across languages and moods.</p>
            </div>
            <div className="lab-card">
              <div className="lab-ico" aria-hidden="true">●</div>
              <h3>Your own clones</h3>
              <p>Custom voices stay private to you until you choose to release them.</p>
            </div>
            <div className="lab-card">
              <div className="lab-ico" aria-hidden="true">∞</div>
              <h3>History, forever</h3>
              <p>Every generation is archived — replay or download whenever you need it.</p>
            </div>
          </div>
        </section>

        {/* ---------- Voices ---------- */}
        <section className="section voices" id="voices">
          <div className="sec-head">
            <p className="eyebrow mono">The library</p>
            <h2 className="sec-title">
              Hear it, <em>before you use it.</em>
            </h2>
          </div>
          <div className="voice-grid">
            {LIBRARY_VOICES.map((v, i) => (
              <article
                className="voice-card"
                key={v.name}
                style={{ '--i': i } as React.CSSProperties}
              >
                <div className="vc-avatar" aria-hidden="true">{v.name[0]}</div>
                <div className="vc-name">{v.name}</div>
                <div className="vc-tag mono">{v.tag}</div>
                <div className="vc-mood">{v.mood}</div>
                <div className="vc-bar"><span style={{ width: `${45 + (i * 9) % 50}%` }} /></div>
              </article>
            ))}
          </div>
          <p className="voices-note">
            …and the entire world of languages. <Link to={user ? '/dashboard/library' : '/register'}>Open the full library →</Link>
          </p>
        </section>

        {/* ---------- CTA ---------- */}
        <section className="cta">
          <div className="cta-inner">
            <p className="eyebrow mono t">Ready when you are</p>
            <h2 className="cta-title">
              Make something<br /><em>worth hearing.</em>
            </h2>
            <Link to={user ? '/dashboard' : '/register'} className="lbtn big ember">
              Start free — no credit card <span aria-hidden="true">↗</span>
            </Link>
            <p className="mono cta-mono">first clone is on us · export in .mp3 · cancel anytime</p>
          </div>
        </section>

        {/* ---------- FAQ ---------- */}
        <section className="section faq" id="faq">
          <div className="sec-head">
            <p className="eyebrow mono">Questions</p>
            <h2 className="sec-title">Sensible answers.</h2>
          </div>
          <div className="faq-list">
            {[
              ['What do I need to clone a voice?', 'About one minute of clean, single-speaker audio. The platform validates the sample and walks you through creating a voice that you can use immediately.'],
              ['Is my cloned voice private?', 'Yes. Voices you clone belong to your account and stay private by default. They only become public if an admin publishes them.'],
              ['What output formats?', 'Every generation is rendered as high-bitrate MP3 you can play back or download instantly from your history.'],
              ['Does it work in other languages?', 'The engine ships with a multilingual model, so a single voice can perform across many languages.'],
            ].map(([q, a]) => (
              <details className="faq-item" key={q}>
                <summary>{q}<span className="plus">+</span></summary>
                <p>{a}</p>
              </details>
            ))}
          </div>
        </section>
      </main>

      {/* ---------- Footer ---------- */}
      <footer className="foot">
        <div className="foot-grid">
          <div className="foot-brand">
            <a className="land-brand" href="#top">
              <span className="land-logo" aria-hidden="true"><i /><i /><i /></span>
              Voxcraft
            </a>
            <p>Voice cloning & text-to-speech, built for people who have something to say.</p>
          </div>
          <div className="foot-col">
            <h4 className="mono">Product</h4>
            <Link to="/dashboard/tts">Studio</Link>
            <Link to="/dashboard/library">Voice library</Link>
            <Link to="/dashboard/my-voices">My voices</Link>
          </div>
          <div className="foot-col">
            <h4 className="mono">Studio</h4>
            <Link to={user ? '/dashboard' : '/login'}>Sign in</Link>
            <Link to={user ? '/dashboard' : '/register'}>Get started</Link>
          </div>
        </div>
        <div className="foot-bottom">
          <span>© {new Date().getFullYear()} Voxcraft</span>
          <span className="mono">designed to be heard.</span>
        </div>
      </footer>
    </div>
  );
}