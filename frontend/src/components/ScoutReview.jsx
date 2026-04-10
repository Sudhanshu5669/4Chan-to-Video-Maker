import React from 'react';
import { Trash2, Check } from 'lucide-react';

export default function ScoutReview({ result, onReject, onAccept }) {
  if (!result) return null;

  return (
    <div className="step-container narrow animate-fade-in">
      <div className="glass-card">
        <h2 className="text-gradient mb-lg">AI Selected Thread</h2>

        <div className="form-stack">
          <div className="scout-info">
            <p className="scout-info-label" style={{ color: 'var(--accent-primary)' }}>
              Thread ID
            </p>
            <p>{result.best_id}</p>
            <p className="text-secondary" style={{ fontSize: '0.85rem', marginTop: '0.3rem' }}>
              Discovered on page {result.currentPage + 1}
            </p>
          </div>

          <div className="scout-info reason">
            <p className="scout-info-label" style={{ color: 'var(--accent-secondary)' }}>
              Why it has potential
            </p>
            <p style={{ fontStyle: 'italic' }}>"{result.reason}"</p>
          </div>

          <div className="scout-info preview">
            <p className="scout-info-label" style={{ color: 'var(--success)' }}>
              Opening Teaser Video Hook
            </p>
            <p>{result.preview}</p>
          </div>
        </div>

        <div className="scout-actions">
          <button className="btn-secondary btn-reject" onClick={onReject}>
            <Trash2 size={16} /> Reject & Keep Searching
          </button>
          <button className="btn-primary" onClick={onAccept}>
            <Check size={16} /> Accept & Curate Replies
          </button>
        </div>
      </div>
    </div>
  );
}
