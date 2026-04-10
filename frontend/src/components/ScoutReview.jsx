import React, { useState } from 'react';
import { Trash2, Check, Trophy, Play, FastForward } from 'lucide-react';

export default function ScoutReview({ result, onReject, onAccept, onNextPage }) {
  if (!result) return null;

  const [activeId, setActiveId] = useState(result.best_id);
  const leaderboard = result.leaderboard || [];

  // Filter out the currently active one to show as runners-up
  const runnersUp = leaderboard.filter(item => item.id !== activeId).slice(0, 5);
  
  const candidates = result.candidates || [];
  
  // Find the selected thread's hook/reason/raw text
  let displayReason = result.reason;
  let displayPreview = result.preview;
  let activeItemRawText = candidates.find(c => c.id === result.best_id)?.text || "No text available.";
  
  if (activeId !== result.best_id) {
    const activeItem = leaderboard.find(i => i.id === activeId);
    if (activeItem) {
      displayReason = `User selected from leaderboard. Score: ${activeItem.score}/10`;
      displayPreview = activeItem.hook || "No hook provided.";
      activeItemRawText = candidates.find(c => c.id === activeId)?.text || "No text available.";
    }
  }

  const handleSelectActive = () => {
    // Pass the activeId back instead of the original AI best_id
    onAccept(activeId);
  };

  return (
    <div className="step-container" style={{ maxWidth: '1000px' }}>
      <div className="review-layout">
        
        {/* Left Panel: Active Selection */}
        <div className="review-panel" style={{ height: '100%' }}>
          <div className="panel-header" style={{ padding: '1.25rem' }}>
            <h2 className="text-gradient" style={{ fontSize: '1.4rem' }}>
              {activeId === result.best_id ? 'AI Editor Pick' : 'Manual Selection'}
            </h2>
          </div>
          <div className="panel-body form-stack" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '1.5rem' }}>
            
            <div className="scout-info">
              <p className="scout-info-label" style={{ color: 'var(--accent-primary)', fontSize: '0.85rem' }}>
                Thread ID
              </p>
              <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>{activeId}</p>
              <p className="text-secondary" style={{ fontSize: '0.8rem', marginTop: '0.3rem' }}>
                Found on page {result.currentPage + 1}
              </p>
            </div>

            <div className="scout-info reason">
               <p className="scout-info-label" style={{ color: 'var(--accent-secondary)' }}>
                Analysis & Rating
              </p>
              <p style={{ fontStyle: 'italic', lineHeight: 1.5 }}>"{displayReason}"</p>
            </div>

            <div className="scout-info preview" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div>
                <p className="scout-info-label" style={{ color: 'var(--success)' }}>
                  Teaser Video Hook
                </p>
                <p style={{ fontSize: '1.05rem', lineHeight: 1.4 }}>{displayPreview}</p>
              </div>
              <div style={{ padding: '0.75rem', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '6px', marginTop: '0.5rem', maxHeight: '150px', overflowY: 'auto' }}>
                <p className="scout-info-label" style={{ color: 'var(--text-secondary)', marginBottom: '0.4rem', fontSize: '0.75rem' }}>
                  Original Thread Text Preview
                </p>
                <p style={{ fontSize: '0.9rem', lineHeight: 1.4, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
                  {activeItemRawText}
                </p>
              </div>
            </div>

            <div className="scout-actions" style={{ marginTop: 'auto', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <button className="btn-secondary btn-reject" onClick={onReject} style={{ flex: 1, minWidth: '140px' }} title="Reject this specific thread">
                <Trash2 size={16} /> Reject
              </button>
              <button className="btn-secondary" onClick={onNextPage} style={{ flex: 1, minWidth: '140px', background: 'rgba(255, 255, 255, 0.05)' }} title="Skip remaining threads and load next page">
                <FastForward size={16} /> Next Page
              </button>
              <button className="btn-primary" onClick={handleSelectActive} style={{ flex: '2 1 100%', minWidth: '200px' }}>
                <Check size={16} /> Accept & Curate
              </button>
            </div>
          </div>
        </div>

        {/* Right Panel: Dankness Leaderboard */}
        <div className="review-panel" style={{ height: '100%' }}>
           <div className="panel-header" style={{ padding: '1rem' }}>
            <div className="flex-center gap-1">
              <Trophy size={18} color="var(--warning)" />
              <h2 style={{ fontSize: '1.1rem' }}>Dankness Leaderboard</h2>
            </div>
            <span className="text-muted" style={{ fontSize: '0.75rem' }}>
              Click to override AI
            </span>
          </div>
          
          <div className="panel-body" style={{ padding: '0.75rem', overflowY: 'auto' }}>
            {runnersUp.length > 0 ? (
              <div className="form-stack">
                {runnersUp.map((item, idx) => (
                  <div 
                    key={item.id} 
                    className="post-item" 
                    style={{ cursor: 'pointer' }}
                    onClick={() => setActiveId(item.id)}
                  >
                    <div className="post-header">
                      <span className="post-id" style={{ color: 'var(--text-secondary)' }}>
                        #{idx + 2} Base Pick
                      </span>
                      <span className="rate-badge" style={{ background: 'rgba(255, 159, 67, 0.2)', color: 'var(--warning)', border: '1px solid rgba(255, 159, 67, 0.4)' }}>
                        Score: {item.score}/10
                      </span>
                    </div>
                    <div className="post-text" style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                      ID: {item.id}
                      <br/>
                      <span style={{ color: 'var(--text-secondary)' }}>Hook: "{item.hook}"</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
               <div className="empty-state">No other valid threads found.</div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
