import React from 'react';

export default function CatalogBrowser({
  selectedBoard,
  catalogPage,
  candidates,
  loading,
  onSelectThread,
  onPrevPage,
  onNextPage,
}) {
  return (
    <div className="step-container wide animate-fade-in">
      <div className="section-header">
        <div className="section-title">
          <h2 className="text-gradient">Catalog Browser</h2>
          <p>/{selectedBoard}/ — Page {catalogPage + 1}</p>
        </div>
        <div className="section-nav">
          <button
            className="btn-secondary"
            onClick={onPrevPage}
            disabled={catalogPage === 0 || loading}
          >
            ← Prev
          </button>
          <button
            className="btn-secondary"
            onClick={onNextPage}
            disabled={loading || candidates.length < 10}
          >
            Next →
          </button>
        </div>
      </div>

      <div className="thread-list">
        {candidates.length > 0 ? (
          candidates.map(c => (
            <div
              key={c.id}
              className="thread-card"
              onClick={() => onSelectThread(c.id)}
            >
              <div className="thread-meta">
                <span className="thread-id">Thread {c.id}</span>
                <span className="reply-badge">{c.replies} replies</span>
              </div>
              <p className="thread-text">{c.text}</p>
            </div>
          ))
        ) : (
          <div className="empty-state">
            No candidates found on this page.
          </div>
        )}
      </div>
    </div>
  );
}
