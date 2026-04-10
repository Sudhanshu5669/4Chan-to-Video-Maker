import React from 'react';
import { Edit3, List, Zap, MonitorPlay, Loader2 } from 'lucide-react';

export default function BoardSelector({
  boards,
  selectedBoard,
  onSelectBoard,
  mode,
  onSetMode,
  loading,
  onSubmit,
}) {
  return (
    <div className="step-container narrow animate-fade-in">
      <div className="glass-card">
        <h2 className="text-gradient mb-lg">Select Target Board</h2>

        <div className="form-stack">
          <select
            value={selectedBoard}
            onChange={e => onSelectBoard(e.target.value)}
            style={{ padding: '1rem', fontSize: '1.05rem' }}
          >
            <option value="">-- Choose a Board --</option>
            {boards.map(b => (
              <option key={b.board} value={b.board}>
                /{b.board}/ - {b.title}
              </option>
            ))}
          </select>

          <div className="form-group">
            <label className="form-label mb-sm">Select Mode:</label>
            <div className="mode-selector">
              <button
                className={`mode-btn ${mode === 'review' ? 'active' : ''}`}
                onClick={() => onSetMode('review')}
              >
                <Edit3 size={16} /> Review
              </button>
              <button
                className={`mode-btn ${mode === 'manual' ? 'active' : ''}`}
                onClick={() => onSetMode('manual')}
              >
                <List size={16} /> Manual
              </button>
              <button
                className={`mode-btn ${mode === 'auto' ? 'active' : ''}`}
                onClick={() => onSetMode('auto')}
              >
                <Zap size={16} /> Auto
              </button>
            </div>
          </div>

          <button
            className="btn-primary"
            onClick={onSubmit}
            disabled={!selectedBoard || loading}
            style={{ marginTop: '0.5rem' }}
          >
            {loading ? (
              <Loader2 className="animate-spin" size={18} />
            ) : mode === 'manual' ? (
              <List size={18} />
            ) : mode === 'auto' ? (
              <Zap size={18} />
            ) : (
              <MonitorPlay size={18} />
            )}
            {loading
              ? 'Processing...'
              : mode === 'manual'
              ? 'Browse Catalog'
              : mode === 'auto'
              ? 'Configure Auto-Render'
              : 'Scout & Curate Thread'}
          </button>
        </div>
      </div>
    </div>
  );
}
