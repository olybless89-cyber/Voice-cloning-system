import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const NAV = [
  { to: '/dashboard/library', label: 'Voice Library', ico: '🎙️' },
  { to: '/dashboard/my-voices', label: 'My Voices', ico: '🗣️' },
  { to: '/dashboard/tts', label: 'Text to Speech', ico: '✨' },
  { to: '/dashboard/history', label: 'History', ico: '🕘' },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">V</div>
          <div>
            <h3>VoiceClone AI</h3>
            <small>Text to speech platform</small>
          </div>
        </div>

        <nav className="nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? 'active' : '')}
            >
              <span className="ico">{item.ico}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
          {user?.is_admin && (
            <NavLink to="/admin" style={{ color: 'var(--accent-2)' }}>
              <span className="ico">🛠️</span>
              <span>Admin Dashboard</span>
            </NavLink>
          )}
        </nav>

        <div className="userbox">
          <div className="name">{user?.full_name || user?.email}</div>
          <div className="mail">{user?.email}</div>
          {user?.is_admin && (
            <button
              className="btn-outline btn-sm"
              style={{ width: '100%', marginTop: 8 }}
              onClick={() => navigate('/admin')}
            >
              Go to Admin
            </button>
          )}
          <div className="actions">
            <button className="btn-ghost btn-sm" onClick={() => navigate('/dashboard/tts')}>
              New Generation
            </button>
            <button className="btn-ghost btn-sm" onClick={logout}>
              Log out
            </button>
          </div>
        </div>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}