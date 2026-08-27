import { mediaUrl } from '../api/client';
import type { Voice } from '../types';

interface Props {
  voice: Voice;
  onUse?: (id: number) => void;
  onDelete?: (id: number) => void;
  onPublish?: (id: number) => void;
  onAdminEdit?: (voice: Voice) => void;
  extraBadge?: React.ReactNode;
  hideUse?: boolean;
}

export default function VoiceCard({
  voice,
  onUse,
  onDelete,
  onPublish,
  onAdminEdit,
  extraBadge,
  hideUse,
}: Props) {
  return (
    <div className="card">
      <div className="title">
        <span>{voice.name}</span>
        <span className={`badge ${voice.status}`}>{voice.status}</span>
        {extraBadge}
      </div>
      <p className="desc">{voice.description || 'No description'}</p>

      {voice.preview_url && (
        <audio controls src={mediaUrl(voice.preview_url)} style={{ width: '100%' }} />
      )}
      {!voice.preview_url && (
        <div className="hint">No preview available</div>
      )}

      <div className="foot">
        {!hideUse && voice.status === 'public' && onUse && (
          <button className="btn-primary btn-sm" onClick={() => onUse(voice.id)}>
            Use Voice
          </button>
        )}
        {onAdminEdit && (
          <button className="btn-outline btn-sm" onClick={() => onAdminEdit(voice)}>
            Edit
          </button>
        )}
        {onPublish && voice.status !== 'public' && (
          <button className="btn-outline btn-sm" onClick={() => onPublish(voice.id)}>
            Publish
          </button>
        )}
        {onDelete && voice.status !== 'deleted' && (
          <button
            className="btn-danger btn-sm"
            onClick={() => onDelete(voice.id)}
          >
            {voice.status === 'public' ? 'Unpublish' : 'Delete'}
          </button>
        )}
      </div>
    </div>
  );
}