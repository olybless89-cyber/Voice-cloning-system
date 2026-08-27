import axios from 'axios';
import type {
  AuthResponse,
  Generation,
  TreeItem,
  User,
  Voice,
  VoiceTree,
} from '../types';

declare global {
  interface Window {
    __BACKEND_API_URL__?: string;
  }
}

// Runtime-injected by the Docker entrypoint when deploying on Railway behind
// the nginx service. When empty, traffic stays same-origin (/api, /uploads)
// and nginx proxies to the backend.
function resolveApiBase(): string {
  if (window.__BACKEND_API_URL__) return window.__BACKEND_API_URL__.replace(/\/$/, '');
  const built = (import.meta.env.VITE_API_BASE as string) ?? '';
  return built.replace(/\/$/, '');
}

export const apiBase: string = resolveApiBase();

const http = axios.create({
  baseURL: `${apiBase}/api`,
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('vc_token');
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem('vc_token');
      localStorage.removeItem('vc_user');
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

function unwrap<T>(p: Promise<{ data: T }>): Promise<T> {
  return p.then((r) => r.data);
}

export const mediaUrl = (path?: string | null): string => {
  if (!path) return '';
  if (path.startsWith('http')) return path;
  return `${apiBase}${path}`;
};

// ---- auth --------------------------------------------------------------
export const api = {
  register(data: { email: string; password: string; full_name?: string }) {
    return unwrap<AuthResponse>(http.post('/auth/register', data));
  },
  login(data: { email: string; password: string }) {
    const body = new URLSearchParams();
    body.set('username', data.email);
    body.set('password', data.password);
    return unwrap<AuthResponse>(
      http.post('/auth/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
    );
  },
  me() {
    return unwrap<User>(http.get('/auth/me'));
  },

  // ---- voices ----
  library() {
    return unwrap<Voice[]>(http.get('/voices/library'));
  },
  mine() {
    return unwrap<Voice[]>(http.get('/voices/mine'));
  },
  tree() {
    return unwrap<VoiceTree>(http.get('/voices/tree'));
  },
  getVoice(id: number) {
    return unwrap<Voice>(http.get(`/voices/${id}`));
  },
  uploadClone(file: File) {
    const form = new FormData();
    form.append('file', file);
    return unwrap<{ id: number; status: string }>(
      http.post('/voices/clone', form)
    );
  },
  finalizeClone(voiceId: number, name: string) {
    return unwrap<Voice>(
      http.post(`/voices/clone/${voiceId}/finalize`, null, {
        params: { name },
      })
    );
  },
  deleteVoice(id: number) {
    return unwrap<{ status: string }>(http.delete(`/voices/${id}`));
  },

  // ---- agent (OpenAI Script Studio) ----
  agentStatus() {
    return unwrap<{ enabled: boolean; model?: string | null; provider: string }>(
      http.get('/agent/status')
    );
  },
  agentRewrite(text: string, tone: string) {
    return unwrap<{ text: string }>(
      http.post('/agent/rewrite', { text, option: tone })
    );
  },
  agentProofread(text: string) {
    return unwrap<{ text: string }>(http.post('/agent/proofread', { text }));
  },
  agentTranslate(text: string, language: string) {
    return unwrap<{ text: string }>(
      http.post('/agent/translate', { text, option: language })
    );
  },
  agentSummarise(text: string, sentences: number) {
    return unwrap<{ text: string }>(
      http.post('/agent/summarise', { text, sentences })
    );
  },
  agentDescribe(name: string) {
    return unwrap<{ text: string }>(
      http.post('/agent/describe', { text: name, option: name })
    );
  },

  // ---- tts ----
  generate(voiceId: number, text: string) {
    return unwrap<Generation>(
      http.post('/tts/generate', { voice_id: voiceId, text })
    );
  },
  history() {
    return unwrap<{ items: Generation[]; total: number }>(
      http.get('/tts/history')
    );
  },
  deleteGeneration(id: number) {
    return unwrap<{ status: string }>(http.delete(`/tts/${id}`));
  },

  // ---- admin ----
  adminUsers() {
    return unwrap<{ users: User[]; total: number }>(http.get('/admin/users'));
  },
  setUserStatus(id: number, is_active: boolean) {
    return unwrap(http.patch(`/admin/users/${id}/status`, { is_active }));
  },
  adminVoices() {
    return unwrap<Voice[]>(http.get('/admin/voices'));
  },
  addPublicVoice(file: File, name: string, description: string) {
    const form = new FormData();
    form.append('file', file);
    form.append('name', name);
    form.append('description', description);
    return unwrap<Voice>(http.post('/admin/voices', form));
  },
  updateAdminVoice(
    id: number,
    data: { name?: string; description?: string; status?: string }
  ) {
    return unwrap<Voice>(http.patch(`/admin/voices/${id}`, data));
  },
  deleteAdminVoice(id: number) {
    return unwrap<{ status: string }>(http.delete(`/admin/voices/${id}`));
  },
  publishUserVoice(id: number) {
    return unwrap<Voice>(http.post(`/admin/voices/${id}/publish`));
  },
  unpublishVoice(id: number) {
    return unwrap<Voice>(http.post(`/admin/voices/${id}/unpublish`));
  },
  userVoices() {
    return unwrap<Voice[]>(http.get('/admin/user-voices'));
  },
  adminGenerations() {
    return unwrap<Generation[]>(http.get('/admin/generations'));
  },
};

export type { TreeItem };