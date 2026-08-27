import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import VoiceCard from '../components/VoiceCard';
import type { Voice } from '../types';

export default function Library() {
  const [voices, setVoices] = useState<Voice[] | null>(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const load = () => {
    api
      .library()
      .then(setVoices)
      .catch((e) => setError(e?.response?.data?.detail || 'Failed to load voices'));
  };

  useEffect(load, []);

  const useVoice = (id: number) => {
    navigate(`/dashboard/tts?voice=${id}`);
  };

  if (error) return <p className="error-text">{error}</p>;
  if (!voices) return <div className="full-loader"><div className="spinner" /></div>;

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Voice Library</h1>
          <p>Browse voices and pick one to start generating speech.</p>
        </div>
        <button className="btn-outline btn-sm" onClick={() => load()}>Refresh</button>
      </div>

      {voices.length === 0 ? (
        <div className="empty">
          <div className="big">🎙️</div>
          <p>No public voices available yet.</p>
          <p className="hint">An admin needs to publish voices.</p>
        </div>
      ) : (
        <div className="grid">
          {voices.map((v) => (
            <VoiceCard key={v.id} voice={v} onUse={useVoice} />
          ))}
        </div>
      )}
    </div>
  );
}