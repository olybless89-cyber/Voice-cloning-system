import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ReadinessBanner from '../components/ReadinessBanner';

export default function Register() {
  const { register } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await register(email, password, fullName || undefined);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <ReadinessBanner />
        <div className="auth-brand">
          <div className="logo">V</div>
          <div>
            <h1>Create account</h1>
            <p>Start generating realistic AI voices</p>
          </div>
        </div>

        <form onSubmit={submit} style={{ marginTop: 18 }}>
          <div className="field">
            <label>Full name (optional)</label>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>
          <div className="field">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="field">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
            <div className="hint">At least 6 characters</div>
          </div>
          {error && <div className="error-text">{error}</div>}
          <button className="btn-primary btn-block" style={{ marginTop: 10 }} disabled={busy}>
            {busy ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="hint" style={{ textAlign: 'center', marginTop: 16 }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}