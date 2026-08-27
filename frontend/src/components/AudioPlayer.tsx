import { useRef, useState } from 'react';
import { mediaUrl } from '../api/client';

interface Props {
  src?: string | null;
  autoPlay?: boolean;
}

export default function AudioPlayer({ src, autoPlay }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  if (!src) return <div className="muted">No audio available</div>;

  const toggle = () => {
    const el = audioRef.current;
    if (!el) return;
    if (el.paused) {
      void el.play().catch(() => setPlaying(false));
      setPlaying(true);
    } else {
      el.pause();
      setPlaying(false);
    }
  };

  return (
    <div className="audio-player">
      <button className="play-btn" onClick={toggle} aria-label="Play/Pause">
        {playing ? '❚❚' : '▶'}
      </button>
      <audio
        ref={audioRef}
        src={mediaUrl(src)}
        controls
        autoPlay={autoPlay}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
      />
    </div>
  );
}