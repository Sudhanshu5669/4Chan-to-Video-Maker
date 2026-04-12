import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import toast, { Toaster } from 'react-hot-toast';
import { MonitorPlay, RefreshCw } from 'lucide-react';
import './index.css';

import BoardSelector from './components/BoardSelector';
import CatalogBrowser from './components/CatalogBrowser';
import ScoutReview from './components/ScoutReview';
import ScriptEditor from './components/ScriptEditor';
import RenderSetup from './components/RenderSetup';
import RenderProgress from './components/RenderProgress';
import DoneScreen from './components/DoneScreen';
import StreamTerminal from './components/StreamTerminal';
import SettingsPanel from './components/SettingsPanel';
import VideoHistory from './components/VideoHistory';
import BatchPipeline from './components/BatchPipeline';

function App() {
  // ── State ───────────────────────────────────────────────────────────────
  const [step, setStep] = useState('board');
  const [mode, setMode] = useState('review');
  const [loading, setLoading] = useState(false);
  const [boards, setBoards] = useState([]);
  const [selectedBoard, setSelectedBoard] = useState('');
  const [voices, setVoices] = useState([]);
  const [musicTracks, setMusicTracks] = useState([]);

  const [candidates, setCandidates] = useState([]);
  const [catalogPage, setCatalogPage] = useState(0);
  const [selectedThread, setSelectedThread] = useState(null);
  const [scoutedThreadResult, setScoutedThreadResult] = useState(null);

  const [playlist, setPlaylist] = useState([]);
  const [otherReplies, setOtherReplies] = useState([]);
  const [page, setPage] = useState(1);
  const itemsPerPage = 25;

  const [renderSettings, setRenderSettings] = useState({
    title: '',
    description: '',
    uploadToYoutube: false,
    ttsRate: 15,
    ttsVoice: 'en-US-ChristopherNeural',
    musicFile: '',
    musicVolume: 0.15,
    startPage: 0,
    randomPage: false,
    ken_burns: false,
  });

  const [renderResult, setRenderResult] = useState(null);
  const [renderProgressValue, setRenderProgressValue] = useState(0);
  const [renderProgressStatus, setRenderProgressStatus] = useState('');

  const [streamingText, setStreamingText] = useState('');
  const [streamingStatus, setStreamingStatus] = useState('');
  const terminalRef = useRef(null);

  // ── Effects ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [streamingText]);

  useEffect(() => {
    fetchBoards();
    fetchVoices();
    fetchMusic();
  }, []);

  // ── Helpers ─────────────────────────────────────────────────────────────
  const formatTtsRate = (val) => `${val >= 0 ? '+' : ''}${val}%`;

  const fetchBoards = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/boards');
      setBoards(res.data.boards || []);
    } catch (err) {
      console.error(err);
      toast.error('Failed to fetch boards from server');
    }
  };

  const fetchVoices = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/voices');
      setVoices(res.data.voices || []);
    } catch (err) {
      console.error('Failed to fetch voices:', err);
    }
  };

  const fetchMusic = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/music');
      setMusicTracks(res.data.tracks || []);
    } catch (err) {
      console.error('Failed to fetch music:', err);
    }
  };

  const fetchStreamingEndpoint = async (url, body, onChunk, onResult) => {
    const res = await fetch(url, {
      method: body ? 'POST' : 'GET',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
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
      buffer = events.pop();

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
          if (eventType === 'chunk' || eventType === 'progress') {
            onChunk(parsed);
          } else if (eventType === 'result') {
            onResult(parsed);
          } else if (eventType === 'error') {
            throw new Error(parsed.error);
          }
        }
      }
    }
  };

  // ── Board Actions ───────────────────────────────────────────────────────
  const handleBoardSubmit = () => {
    if (mode === 'manual') fetchCatalog(selectedBoard, 0);
    else if (mode === 'auto') setStep('render-setup-auto');
    else scoutBoard();
  };

  // ── Scout ───────────────────────────────────────────────────────────────
  const scoutBoard = async (overrideStartPage = null, currentCandidates = []) => {
    if (!selectedBoard) return;
    setLoading(true);
    let currentPage = overrideStartPage !== null 
      ? overrideStartPage 
      : (renderSettings.randomPage ? Math.floor(Math.random() * 10) : renderSettings.startPage);
    let availableCandidates = currentCandidates;
    let foundResult = null;

    while (!foundResult && currentPage < 10) {
      if (availableCandidates.length === 0) {
        setStreamingText('');
        setStreamingStatus(`Fetching catalog page ${currentPage + 1}...`);
        try {
          const res = await axios.get(
            `http://localhost:8000/api/catalog/${selectedBoard}?page=${currentPage}`
          );
          availableCandidates = res.data.candidates || [];
          setCandidates(availableCandidates);
          setCatalogPage(currentPage);
        } catch (err) {
          console.error(err);
          toast.error(`Failed to fetch catalog page ${currentPage + 1}`);
          break;
        }
      }

      if (availableCandidates.length === 0) {
        currentPage++;
        continue;
      }

      setStreamingText('');
      setStreamingStatus(`Scouting threads on page ${currentPage + 1}...`);
      let result = null;
      try {
        await fetchStreamingEndpoint(
          'http://localhost:8000/api/scout_stream',
          { candidates: availableCandidates },
          chunk => setStreamingText(prev => prev + chunk),
          res => { result = res; }
        );
      } catch (err) {
        console.error(err);
        toast.error('Scouting failed');
        break;
      }

      if (result && result.best_id) {
        foundResult = { ...result, currentPage, candidates: availableCandidates };
        break;
      } else {
        setStreamingStatus(
          `No funny/dank threads found on page ${currentPage + 1}. Scrolling to next page...`
        );
        await new Promise(resolve => setTimeout(resolve, 1500));
        availableCandidates = [];
        currentPage++;
      }
    }

    if (foundResult) {
      setScoutedThreadResult(foundResult);
      setSelectedThread(foundResult.best_id);

      if (mode === 'auto') {
        await loadThreadDataStream(selectedBoard, foundResult.best_id, true);
      } else {
        setStep('review-scout');
        setLoading(false);
        setStreamingStatus('');
      }
    } else {
      toast.error('Could not find a good thread after checking multiple pages.');
      setLoading(false);
      setStreamingStatus('');
    }
  };

  // ── Thread Data ─────────────────────────────────────────────────────────
  const loadThreadDataStream = async (board, threadId, autoStartRender = false) => {
    setStreamingText('');
    setStreamingStatus('Curating best replies...');
    try {
      let finalPayload = null;
      await fetchStreamingEndpoint(
        `http://localhost:8000/api/thread_stream/${board}/${threadId}`,
        null,
        chunk => setStreamingText(prev => prev + chunk),
        result => { finalPayload = result; }
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
      toast.error('Failed to load thread data');
    } finally {
      if (mode !== 'auto' || !autoStartRender) {
        setLoading(false);
        setStreamingStatus('');
      }
    }
  };

  // ── Catalog ─────────────────────────────────────────────────────────────
  const fetchCatalog = async (board, pageNum) => {
    setLoading(true);
    try {
      const res = await axios.get(
        `http://localhost:8000/api/catalog/${board}?page=${pageNum}`
      );
      setCandidates(res.data.candidates || []);
      setCatalogPage(pageNum);
      setStep('catalog');
    } catch (err) {
      console.error(err);
      toast.error('Failed to fetch catalog');
    } finally {
      setLoading(false);
    }
  };

  // ── Render (auto mode) ──────────────────────────────────────────────────
  const startRenderDirect = async (board, threadId, currentPlaylist) => {
    setStep('render-progress');
    setLoading(true);
    setStreamingStatus('');
    setRenderProgressValue(0);
    setRenderProgressStatus('Preparing to render...');

    try {
      let finalResult = null;
      await fetchStreamingEndpoint(
        'http://localhost:8000/api/render_stream',
        {
          board,
          thread_id: threadId,
          playlist: currentPlaylist,
          title: renderSettings.title,
          description: renderSettings.description,
          upload_to_youtube: renderSettings.uploadToYoutube,
          tts_rate: formatTtsRate(renderSettings.ttsRate),
          tts_voice: renderSettings.ttsVoice,
          music_file: renderSettings.musicFile,
          music_volume: renderSettings.musicVolume,
          ken_burns: !!renderSettings.ken_burns,
        },
        chunk => {
          if (chunk.progress !== undefined) {
            setRenderProgressValue(chunk.progress);
            setRenderProgressStatus(chunk.status);
          }
        },
        result => { finalResult = result; }
      );

      if (finalResult && finalResult.file) {
        setRenderResult(finalResult);
        setStep('done');
        toast.success('Video rendered successfully!');
      }
    } catch (err) {
      console.error(err);
      toast.error('Video generation failed: ' + err.message);
      setStep('board');
    } finally {
      setLoading(false);
    }
  };

  // ── Render (review mode) ────────────────────────────────────────────────
  const startRender = async () => {
    setStep('render-progress');
    setRenderProgressValue(0);
    setRenderProgressStatus('Starting render process...');

    try {
      let finalResult = null;
      await fetchStreamingEndpoint(
        'http://localhost:8000/api/render_stream',
        {
          board: selectedBoard,
          thread_id: selectedThread,
          playlist,
          title: renderSettings.title,
          description: renderSettings.description,
          upload_to_youtube: renderSettings.uploadToYoutube,
          tts_rate: formatTtsRate(renderSettings.ttsRate),
          tts_voice: renderSettings.ttsVoice,
          music_file: renderSettings.musicFile,
          music_volume: renderSettings.musicVolume,
          ken_burns: !!renderSettings.ken_burns,
        },
        chunk => {
          if (chunk.progress !== undefined) {
            setRenderProgressValue(chunk.progress);
            setRenderProgressStatus(chunk.status);
          }
        },
        result => { finalResult = result; }
      );

      if (finalResult && finalResult.file) {
        setRenderResult(finalResult);
        setStep('done');
        toast.success('Video rendered successfully!');
      }
    } catch (err) {
      console.error(err);
      toast.error('Video generation failed: ' + err.message);
      setStep('review');
    }
  };

  // ── Playlist Actions ────────────────────────────────────────────────────
  const removeReply = index => {
    if (index === 0) return;
    const item = playlist[index];
    setPlaylist(playlist.filter((_, i) => i !== index));
    setOtherReplies([item, ...otherReplies].sort((a, b) => a.id - b.id));
  };

  const addReply = reply => {
    setPlaylist([...playlist, reply]);
    setOtherReplies(otherReplies.filter(r => r.id !== reply.id));
  };

  const moveReply = (index, direction) => {
    if (index === 0) return;
    if (direction === 'up' && index === 1) return;
    if (direction === 'down' && index === playlist.length - 1) return;

    const newPlaylist = [...playlist];
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    [newPlaylist[index], newPlaylist[targetIdx]] = [newPlaylist[targetIdx], newPlaylist[index]];
    setPlaylist(newPlaylist);
  };

  const updateReply = (id, updates) => {
    setPlaylist(playlist.map(p => p.id === id ? { ...p, ...updates } : p));
  };

  // ── Derived ─────────────────────────────────────────────────────────────
  const totalPages = Math.ceil(otherReplies.length / itemsPerPage);
  const currentOtherReplies = otherReplies.slice(
    (page - 1) * itemsPerPage,
    page * itemsPerPage
  );

  // ── Render ──────────────────────────────────────────────────────────────
  return (
    <div className="app-container">
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'rgba(18, 18, 24, 0.95)',
            color: '#eaeaf0',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            backdropFilter: 'blur(16px)',
            borderRadius: '10px',
            fontSize: '0.9rem',
          },
          error: {
            style: { borderColor: 'rgba(255, 71, 87, 0.4)' },
            iconTheme: { primary: '#ff4757', secondary: '#1a1a24' },
          },
          success: {
            style: { borderColor: 'rgba(46, 213, 115, 0.4)' },
            iconTheme: { primary: '#2ed573', secondary: '#1a1a24' },
          },
        }}
      />

      <header className="app-header">
        <div className="flex-center gap-1">
          <MonitorPlay size={26} color="#ff4757" />
          <h1>Auto-Chan Studio</h1>
        </div>
        <div className="flex-center gap-1">
          <button
            className="icon-button"
            onClick={() => setStep('batch')}
            title="Batch Automation"
          >
            Automation
          </button>
          <button
            className="icon-button"
            onClick={() => setStep('history')}
            title="Video History"
          >
            Video History
          </button>
          <button
            className="icon-button"
            onClick={() => setStep('settings')}
            title="Settings"
          >
            Settings
          </button>
          {step !== 'board' && step !== 'settings' && step !== 'history' && step !== 'batch' && (
            <button
              className="btn-secondary"
              onClick={() => {
                setStep('board');
                setPlaylist([]);
                setRenderResult(null);
              }}
            >
              <RefreshCw size={16} /> Start Over
            </button>
          )}
        </div>
      </header>

      <main className="app-main">
        {step === 'board' && (
          <BoardSelector
            boards={boards}
            selectedBoard={selectedBoard}
            onSelectBoard={setSelectedBoard}
            mode={mode}
            onSetMode={setMode}
            loading={loading}
            onSubmit={handleBoardSubmit}
          />
        )}

        {step === 'catalog' && (
          <CatalogBrowser
            selectedBoard={selectedBoard}
            catalogPage={catalogPage}
            candidates={candidates}
            loading={loading}
            onSelectThread={id => {
              setSelectedThread(id);
              setLoading(true);
              loadThreadDataStream(selectedBoard, id, false);
            }}
            onPrevPage={() => fetchCatalog(selectedBoard, Math.max(0, catalogPage - 1))}
            onNextPage={() => fetchCatalog(selectedBoard, catalogPage + 1)}
          />
        )}

        {step === 'render-setup-auto' && (
          <RenderSetup
            selectedBoard={selectedBoard}
            renderSettings={renderSettings}
            onUpdateSettings={setRenderSettings}
            onBack={() => setStep('board')}
            onStartRender={() => scoutBoard()}
            voices={voices}
            musicTracks={musicTracks}
            isAuto
            loading={loading}
          />
        )}

        {step === 'review-scout' && (
          <ScoutReview
            result={scoutedThreadResult}
            onReject={() => {
              const remaining = scoutedThreadResult.candidates.filter(
                c => c.id !== scoutedThreadResult.best_id
              );
              if (remaining.length === 0) {
                 scoutBoard(scoutedThreadResult.currentPage + 1, []);
              } else {
                 scoutBoard(scoutedThreadResult.currentPage, remaining);
              }
            }}
            onNextPage={() => {
              scoutBoard(scoutedThreadResult.currentPage + 1, []);
            }}
            onAccept={(selectedId) => {
              setSelectedThread(selectedId);
              setLoading(true);
              loadThreadDataStream(selectedBoard, selectedId, false);
            }}
          />
        )}

        {step === 'review' && (
          <ScriptEditor
            selectedThread={selectedThread}
            selectedBoard={selectedBoard}
            playlist={playlist}
            currentOtherReplies={currentOtherReplies}
            otherRepliesCount={otherReplies.length}
            page={page}
            totalPages={totalPages}
            onRemoveReply={removeReply}
            onAddReply={addReply}
            onReorder={newReplies => setPlaylist([playlist[0], ...newReplies])}
            onUpdateReply={updateReply}
            onSetPage={setPage}
            onProceed={() => setStep('render-setup')}
            voices={voices}
          />
        )}

        {step === 'render-setup' && (
          <RenderSetup
            selectedBoard={selectedBoard}
            renderSettings={renderSettings}
            onUpdateSettings={setRenderSettings}
            onBack={() => setStep('review')}
            onStartRender={startRender}
            voices={voices}
            musicTracks={musicTracks}
            loading={loading}
          />
        )}

        {step === 'render-progress' && (
          <RenderProgress
            progressValue={renderProgressValue}
            progressStatus={renderProgressStatus}
          />
        )}

        {step === 'done' && (
          <DoneScreen
            renderResult={renderResult}
            onStartOver={() => setStep('board')}
          />
        )}

        {step === 'settings' && (
          <SettingsPanel onBack={() => setStep('board')} />
        )}

        {step === 'history' && (
          <VideoHistory onBack={() => setStep('board')} />
        )}

        {step === 'batch' && (
          <BatchPipeline onBack={() => setStep('board')} />
        )}
      </main>

      <StreamTerminal
        visible={loading && !!streamingStatus}
        streamingStatus={streamingStatus}
        streamingText={streamingText}
        terminalRef={terminalRef}
      />
    </div>
  );
}

export default App;