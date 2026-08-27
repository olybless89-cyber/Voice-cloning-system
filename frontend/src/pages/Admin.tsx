import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, mediaUrl } from '../api/client';
import ReadinessBanner from '../components/ReadinessBanner';
import VoiceCard from '../components/VoiceCard';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import type { Generation, User, Voice } from '../types';

type Tab = 'users' | 'public' | 'user-voices' | 'generations';

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function VoiceModal({ voice, onClose, onSaved }: {
  voice: Voice;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(voice.name);
  const [desc, setDesc] = useState(voice.description || '');
  const [status, setStatus] = useState<Voice['status']>(voice.status);
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();

  const save = async () => {
    setBusy(true);
    try {
      await api.updateAdminVoice(voice.id, {
        name,
        description: desc,
        status: status !== voice.status ? status : undefined,
      });
      toast('Voice updated', 'success');
      onSaved();
      onClose();
    } catch (e: any) {
      toast(e?.response?.data?.detail || 'Failed to update', 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'grid', placeItems: 'center', padding: 20, zIndex: 50 }}>
      <div className="panel" style={{ width: '100%', maxWidth: 460, margin: 0 }}>
        <h3>Edit voice</h3>
        {voice.preview_url && (
          <audio controls src={mediaUrl(voice.preview_url)} style={{ width: '100%' }} />
        )}
        <div className="field">
          <label>Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label>Description</label>
          <textarea rows={2} value={desc} onChange={(e) => setDesc(e.target.value)} />
        </div>
        <div className="field">
          <label>Status</label>
          <select value={status} onChange={(e) => setStatus(e.target.value as Voice['status'])}>
            <option value="public">Public</option>
            <option value="private">Private</option>
            <option value="disabled">Disabled</option>
            <option value="deleted">Deleted</option>
          </select>
        </div>
        <div className="flex-row spread">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={() => void save()} disabled={busy || !name.trim()}>
            {busy ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Admin() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [tab, setTab] = useState<Tab>('users');

  const [users, setUsers] = useState<User[] | null>(null);
  const [publicVoices, setPublicVoices] = useState<Voice[] | null>(null);
  const [userVoices, setUserVoices] = useState<Voice[] | null>(null);
  const [generations, setGenerations] = useState<Generation[] | null>(null);
  const [editing, setEditing] = useState<Voice | null>(null);

  // Add voice form
  const [addOpen, setAddOpen] = useState(false);
  const [newFile, setNewFile] = useState<File | null>(null);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [adding, setAdding] = useState(false);
  const [newPreview, setNewPreview] = useState<string>('');
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    api.adminUsers().then((r) => setUsers(r.users)).catch(() => {});
    api.adminVoices().then(setPublicVoices).catch(() => {});
    api.userVoices().then(setUserVoices).catch(() => {});
    api.adminGenerations().then(setGenerations).catch(() => {});
  }, []);

  useEffect(load, [load]);
  if (!user?.is_admin) {
    return <div className="auth-wrap"><div className="auth-card"><h3>Admins only</h3><p>You do not have access to this area.</p></div></div>;
  }

  const toggleUser = async (id: number, active: boolean) => {
    try {
      await api.setUserStatus(id, active);
      toast(`User ${active ? 'enabled' : 'disabled'}`, 'success');
      load();
    } catch (e: any) {
      toast(e?.response?.data?.detail || 'Failed', 'error');
    }
  };

  const addVoiceNow = async () => {
    if (!newFile || !newName.trim()) {
      toast('Choose a file and enter a name', 'error');
      return;
    }
    setAdding(true);
    try {
      await api.addPublicVoice(newFile, newName.trim(), newDesc.trim());
      toast('Voice published to library', 'success');
      setAddOpen(false);
      setNewFile(null); setNewName(''); setNewDesc(''); setNewPreview('');
      load();
    } catch (e: any) {
      toast(e?.response?.data?.detail || 'Failed to publish', 'error');
    } finally {
      setAdding(false);
    }
  };

  const publishUser = async (id: number) => {
    try {
      await api.publishUserVoice(id);
      toast('Voice published to public library', 'success');
      load();
    } catch (e: any) {
      toast(e?.response?.data?.detail || 'Failed', 'error');
    }
  };

  const unpublish = async (id: number) => {
    try {
      await api.unpublishVoice(id);
      toast('Voice unpublished', 'success');
      load();
    } catch (e: any) {
      toast(e?.response?.data?.detail || 'Failed', 'error');
    }
  };

  const deletePublic = async (id: number) => {
    if (!window.confirm('Delete this voice from the public library?')) return;
    try {
      await api.deleteAdminVoice(id);
      toast('Voice deleted', 'success');
      load();
    } catch (e: any) {
      toast(e?.response?.data?.detail || 'Failed', 'error');
    }
  };

  const onPickFile = (f: File | null) => {
    setNewFile(f);
    if (f) {
      const url = URL.createObjectURL(f);
      setNewPreview(url);
    } else {
      setNewPreview('');
    }
  };

  return (
    <div>
      <ReadinessBanner />
      <div className="page-head">
        <div>
          <h1>Admin Dashboard</h1>
          <p>Manage users, the public voice library, and user voices.</p>
        </div>
        <button className="btn-ghost btn-sm" onClick={() => { logout(); navigate('/login'); }}>
          Log out
        </button>
      </div>

      <div className="tabs">
        <button className={tab === 'users' ? 'active' : ''} onClick={() => setTab('users')}>Users</button>
        <button className={tab === 'public' ? 'active' : ''} onClick={() => setTab('public')}>Voice Library</button>
        <button className={tab === 'user-voices' ? 'active' : ''} onClick={() => setTab('user-voices')}>User Voices</button>
        <button className={tab === 'generations' ? 'active' : ''} onClick={() => setTab('generations')}>Generations</button>
      </div>

      {/* USERS */}
      {tab === 'users' && (
        <div className="panel" style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Joined</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {(users ?? []).map((u) => (
                <tr key={u.id}>
                  <td>{u.id}</td>
                  <td>{u.full_name || '—'}</td>
                  <td>{u.email}</td>
                  <td>{u.is_admin ? <span className="badge public">Admin</span> : <span className="badge private">User</span>}</td>
                  <td className="muted">{fmtDate(u.created_at)}</td>
                  <td>{u.is_active ? 'Active' : <span className="badge deleted">Disabled</span>}</td>
                  <td>
                    {!u.is_admin && (
                      <button className="btn-sm btn-outline" onClick={() => void toggleUser(u.id, !u.is_active)}>
                        {u.is_active ? 'Disable' : 'Enable'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* PUBLIC VOICES */}
      {tab === 'public' && (
        <div>
          <div className="page-head">
            <div><h2>Voice Library</h2><p>Public voices available to all users.</p></div>
            <button className="btn-primary btn-sm" onClick={() => setAddOpen(true)}>+ Add Voice</button>
          </div>

          {addOpen && (
            <div className="panel">
              <h3>Add a public voice</h3>
              <div className="drag-zone" onClick={() => fileRef.current?.click()}>
                <div style={{ fontSize: 28 }}>🎙️</div>
                <div style={{ fontWeight: 600, marginTop: 4 }}>Upload a voice sample</div>
                <div className="tip">{newFile ? newFile.name : 'Click to choose an audio file'}</div>
                <input ref={fileRef} type="file" accept="audio/*" hidden
                  onChange={(e) => onPickFile(e.target.files?.[0] ?? null)} />
              </div>
              {newPreview && (
                <audio controls src={newPreview} style={{ width: '100%', marginTop: 8 }} />
              )}
              <div className="field" style={{ marginTop: 12 }}>
                <label>Voice name</label>
                <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="e.g. Sarah" />
              </div>
              <div className="field">
                <label>Description</label>
                <textarea rows={2} value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="Describe the voice" />
              </div>
              <div className="flex-row spread">
                <button className="btn-ghost" onClick={() => setAddOpen(false)}>Cancel</button>
                <button className="btn-primary" onClick={() => void addVoiceNow()} disabled={adding}>
                  {adding ? 'Publishing…' : 'Publish to library'}
                </button>
              </div>
            </div>
          )}

          {!publicVoices || publicVoices.length === 0 ? (
            <div className="empty"><div className="big">🎙️</div><p>No public voices yet.</p></div>
          ) : (
            <div className="grid">
              {publicVoices.map((v) => (
                <VoiceCard
                  key={v.id}
                  voice={v}
                  onAdminEdit={(voice) => setEditing(voice)}
                  onDelete={v.status === 'public' ? unpublish : deletePublic}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* USER VOICES */}
      {tab === 'user-voices' && (
        <div>
          <div className="page-head"><div><h2>User Voices</h2><p>Voices cloned by users. Promote them to the public library.</p></div></div>
          {!userVoices || userVoices.length === 0 ? (
            <div className="empty"><div className="big">🗣️</div><p>No user-created voices yet.</p></div>
          ) : (
            <div className="grid">
              {userVoices.map((v) => (
                <VoiceCard
                  key={v.id}
                  voice={v}
                  extraBadge={v.owner && <span className="muted" style={{ fontSize: 11 }}>{v.owner.email}</span>}
                  onPublish={publishUser}
                  onDelete={v.status === 'public' ? unpublish : undefined}
                  onAdminEdit={(voice) => setEditing(voice)}
                  hideUse
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* GENERATIONS */}
      {tab === 'generations' && (
        <div className="panel" style={{ overflowX: 'auto' }}>
          <h3 style={{ marginBottom: 12 }}>Generated audio records</h3>
          {!generations || generations.length === 0 ? (
            <div className="empty"><div className="big">🎧</div><p>No generated audio yet.</p></div>
          ) : (
            <table>
              <thead>
                <tr><th>Text</th><th>Voice</th><th>User</th><th>Created</th><th>Audio</th></tr>
              </thead>
              <tbody>
                {generations.map((g) => (
                  <tr key={g.id}>
                    <td style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.text}</td>
                    <td>{g.voice_name || '—'}</td>
                    <td className="muted">{g.user?.email || '—'}</td>
                    <td className="muted">{fmtDate(g.created_at)}</td>
                    <td style={{ minWidth: 220 }}>
                      <audio controls src={mediaUrl(g.audio_url)} style={{ width: '100%', height: 36 }} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {editing && (
        <VoiceModal
          voice={editing}
          onClose={() => setEditing(null)}
          onSaved={load}
        />
      )}
    </div>
  );
}