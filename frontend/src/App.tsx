import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import DashboardLayout from './components/DashboardLayout';
import Library from './pages/Library';
import MyVoices from './pages/MyVoices';
import TTS from './pages/TTS';
import History from './pages/History';
import Admin from './pages/Admin';

function Protected({ children }: { children: React.ReactNode }) {
  const { user, initializing } = useAuth();
  if (initializing) return <FullLoader />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RedirectAfterAuth() {
  const { user } = useAuth();
  if (user?.is_admin) return <Navigate to="/admin" replace />;
  return <Navigate to="/dashboard" replace />;
}

export function FullLoader() {
  return (
    <div className="full-loader">
      <div className="spinner" />
      <p>Loading…</p>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route
        path="/dashboard"
        element={
          <Protected>
            <DashboardLayout />
          </Protected>
        }
      >
        <Route index element={<Navigate to="tts" replace />} />
        <Route path="library" element={<Library />} />
        <Route path="my-voices" element={<MyVoices />} />
        <Route path="tts" element={<TTS />} />
        <Route path="history" element={<History />} />
      </Route>
      <Route
        path="/admin"
        element={
          <Protected>
            <Admin />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function GuestOnly({ children }: { children: React.ReactNode }) {
  const { user, initializing } = useAuth();
  if (initializing) return <FullLoader />;
  if (user) return <RedirectAfterAuth />;
  return <>{children}</>;
}