import React, { useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { Film, Trash2, Youtube, ArrowLeft, Loader2, Play } from 'lucide-react';

export default function VideoHistory({ onBack }) {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [playing, setPlaying] = useState(null);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/history');
      setVideos(res.data.videos || []);
    } catch (err) {
      toast.error('Failed to load video history');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (filename) => {
    try {
      await axios.delete(`http://localhost:8000/api/history/${filename}`);
      toast.success('Video deleted');
      fetchHistory();
      if (playing === filename) setPlaying(null);
    } catch (err) {
      toast.error('Failed to delete video');
    }
  };

  const formatSize = (bytes) => {
    const mb = bytes / (1024 * 1024);
    return mb.toFixed(2) + ' MB';
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  if (loading) {
    return (
      <div className="step-container animate-fade-in flex-center" style={{ minHeight: '60vh' }}>
        <Loader2 className="animate-spin" size={32} color="var(--accent-primary)" />
      </div>
    );
  }

  return (
    <div className="step-container animate-fade-in" style={{ height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
      <div className="section-header">
        <div className="flex-center gap-1">
          <button className="icon-button" onClick={onBack}>
            <ArrowLeft size={20} />
          </button>
          <div className="section-title" style={{ marginLeft: '0.5rem' }}>
            <h2 className="text-gradient flex-center gap-1">
              <Film size={22} /> Render History
            </h2>
            <p>Your previously rendered shorts</p>
          </div>
        </div>
      </div>

      <div className="review-layout" style={{ gridTemplateColumns: playing ? '1fr 1fr' : '1fr' }}>
        {/* Left Side: Video List */}
        <div className="review-panel" style={{ overflowY: 'auto', padding: '1rem' }}>
          {videos.length === 0 ? (
            <div className="empty-state">No videos found. Render something first!</div>
          ) : (
            <div className="form-stack">
              {videos.map(v => (
                <div key={v.filename} className={`post-item ${playing === v.filename ? 'op-post' : ''}`} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                    <div className="post-id">{v.filename}</div>
                    <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                      {formatDate(v.created_at)} • {formatSize(v.size_bytes)}
                    </div>
                  </div>
                  <div className="post-actions" style={{ margin: 0 }}>
                    <button className="icon-button" onClick={() => setPlaying(v.filename)} title="Play">
                      <Play size={16} /> Play
                    </button>
                    <button className="icon-button delete" onClick={() => handleDelete(v.filename)} title="Delete">
                      <Trash2 size={16} /> Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Side: Preview Player */}
        {playing && (
          <div className="review-panel flex-center" style={{ padding: '1rem', background: '#000' }}>
            <video
              controls
              autoPlay
              src={`http://localhost:8000/api/video/${playing}`}
              style={{ width: '100%', maxHeight: '100%', borderRadius: '8px' }}
            >
              Browser unsupported.
            </video>
          </div>
        )}
      </div>
    </div>
  );
}
