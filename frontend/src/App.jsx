import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { ArrowRight, Check, Trash2, Plus, MonitorPlay, Settings, Youtube, Loader2, RefreshCw, Layers, Terminal, ArrowUp, ArrowDown, List, Zap, Edit3 } from 'lucide-react';
import './index.css';

function App() {
  const [step, setStep] = useState('board');
  const [mode, setMode] = useState('review'); // 'review', 'manual', 'auto'
  const [loading, setLoading] = useState(false);
  const [boards, setBoards] = useState([]);
  const [selectedBoard, setSelectedBoard] = useState('');

  const [candidates, setCandidates] = useState([]);
  const [catalogPage, setCatalogPage] = useState(0);
  const [selectedThread, setSelectedThread] = useState(null);

  const [playlist, setPlaylist] = useState([]);
  const [otherReplies, setOtherReplies] = useState([]);
  const [page, setPage] = useState(1);
  const itemsPerPage = 25;

  const [renderSettings, setRenderSettings] = useState({
    title: '',
    description: '',
    uploadToYoutube: false
  });

  const [renderResult, setRenderResult] = useState(null);
  const [renderProgressValue, setRenderProgressValue] = useState(0);
  const [renderProgressStatus, setRenderProgressStatus] = useState('');

  // Streaming State
  const [streamingText, setStreamingText] = useState('');
  const [streamingStatus, setStreamingStatus] = useState('');
  const terminalRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [streamingText]);

  // Fetch Boards on mount
  useEffect(() => {
    fetchBoards();
  }, []);

  const fetchBoards = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/boards');
      setBoards(res.data.boards || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchStreamingEndpoint = async (url, body, onChunk, onResult) => {
    try {
      const res = await fetch(url, {
        method: body ? 'POST' : 'GET',
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined
      });
      if (!res.ok) throw new Error('Network response was not ok');
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop(); // keep last chunk in buffer

        for (const event of events) {
          let eventType = 'message';
          let eventData = '';
          const lines = event.split('\n');
          for (const line of lines) {
            if (line.startsWith('event: ')) eventType = line.trim().substring(7);
            else if (line.startsWith('data: ')) eventData = line.trim().substring(6);
          }
          if (eventData) {
            const parsed = JSON.parse(eventData);
            if (eventType === 'chunk') {
              onChunk(parsed);
            } else if (eventType === 'result') {
              onResult(parsed);
            } else if (eventType === 'error') {
              throw new Error(parsed.error);
            }
          }
        }
      }
    } catch (err) {
      throw err;
    }
  };

  const scoutBoard = async () => {
    if (!selectedBoard) return;
    setLoading(true);
    setStreamingText('');
    setStreamingStatus('Scouting threads...');
    try {
      const res = await axios.get(`http://localhost:8000/api/catalog/${selectedBoard}`);
      if (res.data.candidates) {
        setCandidates(res.data.candidates);
        let bestId = null;

        await fetchStreamingEndpoint(
          'http://localhost:8000/api/scout_stream',
          { candidates: res.data.candidates },
          (chunk) => setStreamingText(prev => prev + chunk),
          (result) => { bestId = result.best_id; }
        );

        if (bestId) {
          setSelectedThread(bestId);
          await loadThreadDataStream(selectedBoard, bestId, true);
        } else {
          alert('Could not find a good thread.');
          setLoading(false);
          setStreamingStatus('');
        }
      }
    } catch (err) {
      console.error(err);
      alert('Failed to scout board');
      setLoading(false);
      setStreamingStatus('');
    }
  };

  const loadThreadDataStream = async (board, threadId, autoStartRender = false) => {
    setStreamingText('');
    setStreamingStatus('Curating best replies...');
    try {
      let finalPayload = null;
      await fetchStreamingEndpoint(
        `http://localhost:8000/api/thread_stream/${board}/${threadId}`,
        null,
        (chunk) => setStreamingText(prev => prev + chunk),
        (result) => { finalPayload = result; }
      );

      if (finalPayload) {
        const { op, selected_replies, other_replies } = finalPayload;
        const currentPlaylist = [op, ...selected_replies];
        setPlaylist(currentPlaylist);
        setOtherReplies(other_replies);

        if (mode === 'auto' && autoStartRender) {
          await startRenderDirect(board, threadId, currentPlaylist);
        } else {
          setStep('review');
        }
      }
    } catch (err) {
      console.error(err);
      alert('Failed to load thread data');
    } finally {
      if (mode !== 'auto' || !autoStartRender) {
        setLoading(false);
        setStreamingStatus('');
      }
    }
  };

  const fetchCatalog = async (board, pageNum) => {
    setLoading(true);
    try {
      const res = await axios.get(`http://localhost:8000/api/catalog/${board}?page=${pageNum}`);
      setCandidates(res.data.candidates || []);
      setCatalogPage(pageNum);
      setStep('catalog');
    } catch (err) {
      console.error(err);
      alert('Failed to fetch catalog');
    } finally {
      setLoading(false);
    }
  };

  const startRenderDirect = async (board, threadId, currentPlaylist) => {
    setStep('render-progress');
    setLoading(true);
    setStreamingStatus('');
    setRenderProgressValue(0);
    setRenderProgressStatus('Preparing to render...');

    try {
      let finalResult = null;
      await fetchStreamingEndpoint('http://localhost:8000/api/render_stream', {
        board: board,
        thread_id: threadId,
        playlist: currentPlaylist,
        title: renderSettings.title,
        description: renderSettings.description,
        upload_to_youtube: renderSettings.uploadToYoutube
      },
        (chunk) => {
          if (chunk.progress !== undefined) {
            setRenderProgressValue(chunk.progress);
            setRenderProgressStatus(chunk.status);
          }
        },
        (result) => { finalResult = result; }
      );

      if (finalResult && finalResult.file) {
        setRenderResult(finalResult);
        setStep('done');
      }
    } catch (err) {
      console.error(err);
      alert('Video generation failed: ' + err.message);
      setStep('board');
    } finally {
      setLoading(false);
    }
  };

  const removeReply = (index) => {
    if (index === 0) return; // Don't remove OP
    const item = playlist[index];
    setPlaylist(playlist.filter((_, i) => i !== index));
    setOtherReplies([item, ...otherReplies].sort((a, b) => a.id - b.id)); // Add back to other replies
  };

  const addReply = (reply) => {
    setPlaylist([...playlist, reply]);
    setOtherReplies(otherReplies.filter(r => r.id !== reply.id));
  };

  const moveReply = (index, direction) => {
    if (index === 0) return; // OP stays at the top
    if (direction === 'up' && index === 1) return; // Already first reply
    if (direction === 'down' && index === playlist.length - 1) return; // Already at bottom

    const newPlaylist = [...playlist];
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    [newPlaylist[index], newPlaylist[targetIdx]] = [newPlaylist[targetIdx], newPlaylist[index]];
    setPlaylist(newPlaylist);
  };

  const startRender = async () => {
    setStep('render-progress');
    setRenderProgressValue(0);
    setRenderProgressStatus('Starting render process...');

    try {
      let finalResult = null;
      await fetchStreamingEndpoint('http://localhost:8000/api/render_stream', {
        board: selectedBoard,
        thread_id: selectedThread,
        playlist: playlist,
        title: renderSettings.title,
        description: renderSettings.description,
        upload_to_youtube: renderSettings.uploadToYoutube
      },
        (chunk) => {
          if (chunk.progress !== undefined) {
            setRenderProgressValue(chunk.progress);
            setRenderProgressStatus(chunk.status);
          }
        },
        (result) => { finalResult = result; }
      );

      if (finalResult && finalResult.file) {
        setRenderResult(finalResult);
        setStep('done');
      }
    } catch (err) {
      console.error(err);
      alert('Video generation failed: ' + err.message);
      setStep('review');
    }
  };

  // Pagination Logic
  const totalPages = Math.ceil(otherReplies.length / itemsPerPage);
  const currentOtherReplies = otherReplies.slice((page - 1) * itemsPerPage, page * itemsPerPage);

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="flex-center gap-2">
          <MonitorPlay size={28} color="#ff4757" />
          <h1>Auto-Chan Studio</h1>
        </div>
        <div>
          {step !== 'board' && (
            <button className="btn-secondary" onClick={() => {
              setStep('board');
              setPlaylist([]);
            }}>
              <RefreshCw size={18} /> Start Over
            </button>
          )}
        </div>
      </header>

      <main className="app-main">
        {step === 'board' && (
          <div className="animate-fade-in" style={{ maxWidth: '600px', margin: '0 auto', width: '100%' }}>
            <div className="glass-card">
              <h2 style={{ marginBottom: '1rem' }} className="text-gradient">Select Target Board</h2>

              <div style={{ display: 'flex', gap: '1rem', flexDirection: 'column' }}>
                <select
                  value={selectedBoard}
                  onChange={e => setSelectedBoard(e.target.value)}
                  style={{ padding: '1rem', fontSize: '1.1rem' }}
                >
                  <option value="">-- Choose a Board --</option>
                  {boards.map(b => (
                    <option key={b.board} value={b.board}>/{b.board}/ - {b.title}</option>
                  ))}
                </select>

                <div style={{ marginTop: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Select Mode:</label>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      className={`btn-secondary ${mode === 'review' ? 'active-mode' : ''}`}
                      style={{ flex: 1, border: mode === 'review' ? '2px solid var(--accent-primary)' : '' }}
                      onClick={() => setMode('review')}
                    >
                      <Edit3 size={18} /> Review
                    </button>
                    <button
                      className={`btn-secondary ${mode === 'manual' ? 'active-mode' : ''}`}
                      style={{ flex: 1, border: mode === 'manual' ? '2px solid var(--accent-primary)' : '' }}
                      onClick={() => setMode('manual')}
                    >
                      <List size={18} /> Manual
                    </button>
                    <button
                      className={`btn-secondary ${mode === 'auto' ? 'active-mode' : ''}`}
                      style={{ flex: 1, border: mode === 'auto' ? '2px solid var(--accent-primary)' : '' }}
                      onClick={() => setMode('auto')}
                    >
                      <Zap size={18} /> Auto
                    </button>
                  </div>
                </div>

                <button
                  className="btn-primary"
                  onClick={() => {
                    if (mode === 'manual') fetchCatalog(selectedBoard, 0);
                    else if (mode === 'auto') setStep('render-setup-auto');
                    else scoutBoard();
                  }}
                  disabled={!selectedBoard || loading}
                  style={{ marginTop: '1rem' }}
                >
                  {loading ? <Loader2 className="animate-spin" /> : (mode === 'manual' ? <List /> : (mode === 'auto' ? <Zap /> : <MonitorPlay />))}
                  {loading ? 'Processing...' : (mode === 'manual' ? 'Browse Catalog' : (mode === 'auto' ? 'Configure Auto-Render' : 'Scout & Curate Thread'))}
                </button>
              </div>
            </div>
          </div>
        )}

        {step === 'catalog' && (
          <div className="animate-fade-in" style={{ maxWidth: '800px', margin: '0 auto', width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '1.5rem' }}>
              <div>
                <h2 className="text-gradient">Catalog Browser</h2>
                <p style={{ color: 'var(--text-secondary)' }}>/{selectedBoard}/ - Page {catalogPage + 1}</p>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn-secondary" onClick={() => fetchCatalog(selectedBoard, catalogPage > 0 ? catalogPage - 1 : 0)} disabled={catalogPage === 0 || loading}>Prev Page</button>
                <button className="btn-secondary" onClick={() => fetchCatalog(selectedBoard, catalogPage + 1)} disabled={loading || candidates.length < 10}>Next Page</button>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {candidates.length > 0 ? candidates.map(c => (
                <div key={c.id} className="glass-card" style={{ cursor: 'pointer', transition: 'all 0.2s', padding: '1rem' }} onClick={() => {
                  setSelectedThread(c.id);
                  setLoading(true);
                  loadThreadDataStream(selectedBoard, c.id, false);
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: 'bold', color: 'var(--accent-primary)' }}>Thread {c.id}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{c.replies} replies</span>
                  </div>
                  <p>{c.text}</p>
                </div>
              )) : (
                <div className="flex-center" style={{ padding: '3rem', color: 'var(--text-secondary)' }}>No candidates found on this page.</div>
              )}
            </div>
          </div>
        )}

        {step === 'render-setup-auto' && (
          <div className="animate-fade-in" style={{ maxWidth: '600px', margin: '0 auto', width: '100%' }}>
            <div className="glass-card">
              <h2 className="text-gradient" style={{ marginBottom: '1.5rem' }}>Auto-Render Settings</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                The AI will automatically scout the best thread, curate it, and render the video using these settings.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                    YouTube Title
                  </label>
                  <input
                    type="text"
                    placeholder={`4chan /${selectedBoard}/ is actually unhinged 💀`}
                    value={renderSettings.title}
                    onChange={e => setRenderSettings({ ...renderSettings, title: e.target.value })}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                    Description
                  </label>
                  <textarea
                    rows={4}
                    placeholder="They really said that... #shorts"
                    value={renderSettings.description}
                    onChange={e => setRenderSettings({ ...renderSettings, description: e.target.value })}
                  ></textarea>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', background: 'rgba(0,0,0,0.3)', borderRadius: '8px' }}>
                  <div className="flex-center gap-2">
                    <Youtube color="#ff0000" size={24} />
                    <span style={{ fontWeight: '600' }}>Auto-Upload to YouTube</span>
                  </div>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={renderSettings.uploadToYoutube}
                      onChange={e => setRenderSettings({ ...renderSettings, uploadToYoutube: e.target.checked })}
                    />
                    <span className="slider"></span>
                  </label>
                </div>

                <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                  <button className="btn-secondary" onClick={() => setStep('board')} style={{ flex: 1 }}>
                    Back
                  </button>
                  <button className="btn-primary" onClick={() => {
                    scoutBoard();
                  }} style={{ flex: 2 }}>
                    <Zap /> Start Automation
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {step === 'review' && (
          <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '1.5rem' }}>
              <div>
                <h2 className="text-gradient">Review Script</h2>
                <p style={{ color: 'var(--text-secondary)' }}>Thread {selectedThread} from /{selectedBoard}/</p>
              </div>
              <button className="btn-primary" onClick={() => setStep('render-setup')}>
                Proceed to Render <ArrowRight size={18} />
              </button>
            </div>

            <div className="review-layout">
              {/* Left Panel: Selected Playlist */}
              <div className="review-panel">
                <div className="panel-header">
                  <div className="flex-center gap-2">
                    <Layers size={20} color="var(--accent-secondary)" />
                    <h2>Current Script ({playlist.length})</h2>
                  </div>
                </div>
                <div className="panel-body">
                  {playlist.map((post, idx) => (
                    <div key={post.id} className="post-item">
                      <div className="post-header">
                        <span className="post-id">{idx === 0 ? 'OP' : `Reply >>${post.id}`}</span>
                        {idx > 0 && (
                          <div style={{ display: 'flex', gap: '0.2rem' }}>
                            <button className="icon-button" onClick={() => moveReply(idx, 'up')} disabled={idx === 1} title="Move Up">
                              <ArrowUp size={16} />
                            </button>
                            <button className="icon-button" onClick={() => moveReply(idx, 'down')} disabled={idx === playlist.length - 1} title="Move Down">
                              <ArrowDown size={16} />
                            </button>
                          </div>
                        )}
                      </div>
                      <div className="post-text">{post.text}</div>
                      {idx > 0 && (
                        <div className="post-actions">
                          <button className="icon-button delete" onClick={() => removeReply(idx)} title="Remove">
                            <Trash2 size={18} /> Remove
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Right Panel: Other Replies */}
              <div className="review-panel">
                <div className="panel-header">
                  <h2>Other Replies ({otherReplies.length})</h2>
                </div>
                <div className="panel-body">
                  {otherReplies.length > 0 ? currentOtherReplies.map((post) => (
                    <div key={post.id} className="post-item">
                      <div className="post-header">
                        <span className="post-id">Reply {'>'}{post.id}</span>
                      </div>
                      <div className="post-text">{post.text}</div>
                      <div className="post-actions">
                        <button className="icon-button add" onClick={() => addReply(post)} title="Add to Script">
                          <Plus size={18} /> Add
                        </button>
                      </div>
                    </div>
                  )) : (
                    <div style={{ textAlign: 'center', margin: '2rem', color: 'var(--text-secondary)' }}>
                      No more replies.
                    </div>
                  )}

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="pagination">
                      <button disabled={page === 1} onClick={() => setPage(page - 1)}>←</button>
                      <span>{page} / {totalPages}</span>
                      <button disabled={page === totalPages} onClick={() => setPage(page + 1)}>→</button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {step === 'render-setup' && (
          <div className="animate-fade-in" style={{ maxWidth: '600px', margin: '0 auto', width: '100%' }}>
            <div className="glass-card">
              <h2 className="text-gradient" style={{ marginBottom: '1.5rem' }}>Render Settings</h2>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                    YouTube Title
                  </label>
                  <input
                    type="text"
                    placeholder={`4chan /${selectedBoard}/ is actually unhinged 💀`}
                    value={renderSettings.title}
                    onChange={e => setRenderSettings({ ...renderSettings, title: e.target.value })}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                    Description
                  </label>
                  <textarea
                    rows={4}
                    placeholder="They really said that... #shorts"
                    value={renderSettings.description}
                    onChange={e => setRenderSettings({ ...renderSettings, description: e.target.value })}
                  ></textarea>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', background: 'rgba(0,0,0,0.3)', borderRadius: '8px' }}>
                  <div className="flex-center gap-2">
                    <Youtube color="#ff0000" size={24} />
                    <span style={{ fontWeight: '600' }}>Auto-Upload to YouTube</span>
                  </div>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={renderSettings.uploadToYoutube}
                      onChange={e => setRenderSettings({ ...renderSettings, uploadToYoutube: e.target.checked })}
                    />
                    <span className="slider"></span>
                  </label>
                </div>

                <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                  <button className="btn-secondary" onClick={() => setStep('review')} style={{ flex: 1 }}>
                    Back
                  </button>
                  <button className="btn-primary" onClick={startRender} style={{ flex: 2 }}>
                    <MonitorPlay /> Start Render
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {step === 'render-progress' && (
          <div className="animate-fade-in flex-center" style={{ flexDirection: 'column', height: '100%' }}>
            <div className="glass-card" style={{ textAlign: 'center', padding: '4rem', width: '100%', maxWidth: '500px' }}>
              <MonitorPlay size={48} className="text-gradient" style={{ margin: '0 auto 1.5rem', display: 'block' }} />
              <h2 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>Rendering Video</h2>

              <div className="progress-container">
                <div className="progress-fill" style={{ width: `${renderProgressValue}%` }}></div>
              </div>

              <div className="progress-status text-gradient">
                {renderProgressStatus} ({renderProgressValue}%)
              </div>

              <p style={{ color: 'var(--text-secondary)', marginTop: '2rem', fontSize: '0.9rem' }}>
                Please do not close this window.
              </p>
            </div>
          </div>
        )}

        {step === 'done' && renderResult && (
          <div className="animate-fade-in flex-center" style={{ flexDirection: 'column', height: '100%' }}>
            <div className="glass-card" style={{ textAlign: 'center', maxWidth: '500px' }}>
              <div style={{ background: 'rgba(46, 213, 115, 0.2)', width: '80px', height: '80px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem' }}>
                <Check size={40} color="#2ed573" />
              </div>
              <h2 className="text-gradient" style={{ fontSize: '2rem', marginBottom: '1rem' }}>Video Ready!</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
                Rendered successfully to: {renderResult.file}
              </p>

              {renderResult.uploaded && (
                <div style={{ background: 'rgba(255, 0, 0, 0.1)', border: '1px solid rgba(255,0,0,0.3)', padding: '1rem', borderRadius: '8px', marginBottom: '2rem' }}>
                  <p style={{ color: '#ff4757', fontWeight: 'bold' }}>Successfully Uploaded to YouTube!</p>
                </div>
              )}

              <button className="btn-primary" onClick={() => setStep('board')}>
                Create Another Video
              </button>
            </div>
          </div>
        )}

      </main>

      {/* LLM Streaming Terminal Overlay */}
      {loading && streamingStatus && (
        <div className="stream-terminal" ref={terminalRef}>
          <div className="stream-terminal-header">
            <Terminal size={16} /> {streamingStatus} <Loader2 size={14} className="animate-spin" style={{ marginLeft: 'auto' }} />
          </div>
          <div className="stream-content">
            {streamingText}
            <span className="stream-cursor"></span>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;