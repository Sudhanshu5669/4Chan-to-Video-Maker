import React from 'react';
import { Check, Play } from 'lucide-react';

export default function DoneScreen({ renderResult, onStartOver }) {
  if (!renderResult) return null;

  const filename = renderResult.file.split(/[/\\]/).pop();
  const videoUrl = `http://localhost:8000/api/video/${filename}`;

  return (
    <div className="step-container narrow animate-fade-in flex-center" style={{ height: '100%' }}>
      <div className="glass-card done-card">
        <div className="success-icon">
          <Check size={38} color="var(--success)" />
        </div>

        <h2 className="text-gradient" style={{ fontSize: '1.8rem', marginBottom: '0.75rem' }}>
          Video Ready!
        </h2>

        {/* Video Preview Player */}
        <div style={{ marginBottom: '1.5rem' }}>
          <video
            controls
            src={videoUrl}
            style={{
              width: '100%',
              maxHeight: '360px',
              borderRadius: '12px',
              background: '#000',
            }}
          >
            Your browser does not support video playback.
          </video>
        </div>

        <p className="text-secondary mb-lg" style={{ fontSize: '0.85rem' }}>
          Saved to: <strong>{renderResult.file}</strong>
        </p>

        {renderResult.uploaded && (
          <div className="youtube-badge">
            <p>✅ Successfully Uploaded to YouTube!</p>
          </div>
        )}

        <button className="btn-primary" onClick={onStartOver}>
          Create Another Video
        </button>
      </div>
    </div>
  );
}
