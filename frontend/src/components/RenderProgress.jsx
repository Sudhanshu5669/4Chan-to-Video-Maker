import React from 'react';
import { MonitorPlay } from 'lucide-react';

export default function RenderProgress({ progressValue, progressStatus }) {
  return (
    <div className="step-container narrow animate-fade-in flex-center" style={{ height: '100%' }}>
      <div className="glass-card progress-card">
        <MonitorPlay size={44} style={{ color: 'var(--accent-primary)', margin: '0 auto 1.5rem', display: 'block' }} />
        <h2 style={{ fontSize: '1.4rem', marginBottom: '0.3rem' }}>Rendering Video</h2>

        <div className="progress-container">
          <div className="progress-fill" style={{ width: `${progressValue}%` }} />
        </div>

        <div className="progress-status text-gradient">
          {progressStatus} ({progressValue}%)
        </div>

        <p className="text-muted" style={{ marginTop: '1.5rem', fontSize: '0.85rem' }}>
          Please do not close this window.
        </p>
      </div>
    </div>
  );
}
