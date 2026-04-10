import React, { useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { Layers, Play, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

export default function BatchPipeline({ onBack }) {
  const [activeJobs, setActiveJobs] = useState([]);
  const [history, setHistory] = useState([]);
  const [queueSize, setQueueSize] = useState(0);

  const [boards, setBoards] = useState([]);
  const [voices, setVoices] = useState([]);
  const [musicTracks, setMusicTracks] = useState([]);

  const [form, setForm] = useState({
    board: 'b',
    amount: 1,
    tts_voice: 'en-US-ChristopherNeural',
    tts_rate: '+15%',
    music_file: '',
    music_volume: 0.15
  });

  const [enqueueing, setEnqueueing] = useState(false);

  useEffect(() => {
    fetchFormAssets();
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchFormAssets = async () => {
    try {
      const [brd, vc, msc] = await Promise.all([
        axios.get('http://localhost:8000/api/boards'),
        axios.get('http://localhost:8000/api/voices'),
        axios.get('http://localhost:8000/api/music')
      ]);
      setBoards(brd.data.boards || []);
      setVoices(vc.data.voices || []);
      setMusicTracks(msc.data.tracks || []);
    } catch(err) {
      console.warn("Could not load batch form assets.");
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/batch/status');
      setActiveJobs(res.data.active || []);
      setHistory(res.data.history || []);
      setQueueSize(res.data.queue_size || 0);
    } catch (err) {
       // silently skip polling failures
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type } = e.target;
    setForm(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) : value
    }));
  };

  const handleEnqueue = async (e) => {
    e.preventDefault();
    setEnqueueing(true);
    try {
      await axios.post('http://localhost:8000/api/batch', form);
      toast.success(`Enqueued ${form.amount} jobs targeting /${form.board}/`);
      fetchStatus();
    } catch(err) {
      toast.error('Failed to submit batch job.');
    } finally {
      setEnqueueing(false);
    }
  };

  return (
    <div className="step-container animate-fade-in" style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) 2fr', gap: '2rem', maxWidth: '1200px' }}>
      
      {/* LEFT: Enqueue Menu */}
      <div className="glass-card" style={{ alignSelf: 'start' }}>
        <div className="panel-header" style={{ background: 'transparent', padding: '0 0 1rem 0' }}>
          <div className="flex-center gap-1">
            <Layers size={22} color="var(--accent-primary)" />
            <h2 className="text-gradient">Batch Queue</h2>
          </div>
          <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
            Fully automate background rendering overnight. Disables manual GUI curation.
          </p>
        </div>

        <form className="form-stack" onSubmit={handleEnqueue}>
          <div className="form-group">
            <label className="form-label">Target Board</label>
            <select name="board" value={form.board} onChange={handleInputChange} required>
              {boards.map(b => (
                <option key={b.board} value={b.board}>/{b.board}/ - {b.title}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Number of Videos</label>
            <input type="number" name="amount" min="1" max="25" value={form.amount} onChange={handleInputChange} required />
          </div>

          <div className="form-group">
             <label className="form-label">TTS Voice</label>
             <select name="tts_voice" value={form.tts_voice} onChange={handleInputChange}>
              {voices.map((v, i) => (
                <option key={i} value={v.name}>{v.name} {v.gender === 'Female' ? '♀' : '♂'}</option>
              ))}
             </select>
          </div>

          <div className="form-group">
             <label className="form-label">Background Music</label>
             <select name="music_file" value={form.music_file} onChange={handleInputChange}>
               <option value="">None (TTS Only)</option>
               {musicTracks.map(t => (
                 <option key={t.file} value={t.file}>{t.name}</option>
               ))}
             </select>
          </div>

          <div className="render-actions" style={{ marginTop: '1.5rem' }}>
            <button type="submit" className="btn-primary w-full" disabled={enqueueing} style={{ justifyContent: 'center' }}>
               {enqueueing ? <Loader2 className="animate-spin" size={16}/> : <Play size={16}/>}
               Add to Queue
            </button>
          </div>
        </form>
      </div>

      {/* RIGHT: Active / History Tables */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        
        {/* Active Jobs */}
        <div className="glass-card" style={{ flex: 1, padding: '1.5rem' }}>
          <h3 className="text-primary mb-md" style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Active Operations</span>
            <span className="rate-badge">{queueSize} in Queue</span>
          </h3>
          
          <div className="form-stack" style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {activeJobs.length === 0 ? (
               <div className="empty-state" style={{ padding: '2rem' }}>Queue is idle. No jobs running.</div>
            ) : (
              activeJobs.map(job => (
                <div key={job.id} className={`post-item ${job.status === 'running' ? 'active-drag' : ''}`} style={{ borderColor: job.status === 'running' ? 'var(--accent-primary)' : '' }}>
                   <div className="flex-center" style={{ justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                     <span className="post-id" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {job.status === 'running' && <Loader2 size={14} className="animate-spin" color="var(--accent-primary)" />}
                        Job {job.id} (/{job.config.board}/)
                     </span>
                     <span className="rate-badge">{job.progress}%</span>
                   </div>
                   
                   {job.status === 'running' && (
                      <div className="progress-bar-container" style={{ height: '4px', marginBottom: '0.5rem' }}>
                        <div className="progress-bar-fill animate-shimmer" style={{ width: `${job.progress}%` }}></div>
                      </div>
                   )}
                   
                   <div className="text-secondary" style={{ fontSize: '0.8rem' }}>
                     &gt; {job.log}
                   </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* History Log */}
         <div className="glass-card" style={{ flex: 1, padding: '1.5rem' }}>
          <h3 className="text-primary mb-md">Recent Executions</h3>
          
           <div className="form-stack" style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {history.length === 0 ? (
               <div className="text-muted" style={{ fontSize: '0.85rem' }}>No recent history.</div>
            ) : (
              history.map(job => (
                <div key={job.id} className="post-item" style={{ flexDirection: 'row', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem' }}>
                  {job.status === 'completed' ? <CheckCircle2 size={18} color="var(--success)"/> : <XCircle size={18} color="var(--danger)"/>}
                  <div style={{ flex: 1 }}>
                     <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>Job {job.id}</div>
                     <div className="text-red" style={{ fontSize: '0.75rem', color: job.status === 'failed' ? 'var(--danger)' : 'var(--text-secondary)' }}>
                       {job.status === 'failed' ? job.log : 'Successfully rendered and saved.'}
                     </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
