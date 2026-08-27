export interface User {
  id: number;
  email: string;
  full_name?: string | null;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Voice {
  id: number;
  name: string;
  description?: string | null;
  kind: 'public' | 'clone';
  status: 'processing' | 'private' | 'public' | 'disabled' | 'deleted';
  audio_url?: string | null;
  preview_url?: string | null;
  created_at: string;
  owner?: { id: number; email: string } | null;
}

export interface Generation {
  id: number;
  text: string;
  voice_id?: number | null;
  voice_name?: string | null;
  audio_url: string;
  duration_seconds?: number | null;
  created_at: string;
  user?: { id: number; email: string } | null;
}

export interface TreeItem {
  id: number;
  name: string;
  description?: string | null;
  kind: string;
  status: string;
  preview_url?: string | null;
}

export interface VoiceTree {
  library: TreeItem[];
  mine: TreeItem[];
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}