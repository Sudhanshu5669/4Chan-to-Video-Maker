import React from 'react';
import { Youtube, MonitorPlay, Zap, Volume2, Mic, Music } from 'lucide-react';

export default function RenderSetup({
  selectedBoard,
  renderSettings,
  onUpdateSettings,
  onBack,
  onStartRender,
  isAuto = false,
  loading,
  voices = [],
  musicTracks = [],
}) {
  const formatRate = val => `${val >= 0 ? '+' : ''}${val}%`;

  const formatVoiceName = v => {
    const parts = v.name.split('-');
    const region = parts.length >= 2 ? parts[1] : '';
    const rawName = parts.slice(2).join('-');
    const name = rawName.replace('Neural', '').replace('Multilingual', '');
    const glyph = v.gender === 'Male' ? '♂' : '♀';
    return `${name} (${region}) ${glyph}`;
  };

  return (
    <div className="step-container narrow animate-fade-in">
      <div className="glass-card">
        <h2 className="text-gradient mb-lg">
          {isAuto ? 'Auto-Render Settings' : 'Render Settings'}
        </h2>

        {isAuto && (
          <p className="text-secondary mb-lg">
            The AI will automatically scout the best thread, curate it, and render
            the video using these settings.
          </p>
        )}

        <div className="form-stack">
          {/* Title */}
          <div className="form-group">
            <label className="form-label">YouTube Title</label>
            <input
              type="text"
              placeholder={`4chan /${selectedBoard}/ is actually unhinged 💀`}
              value={renderSettings.title}
              onChange={e =>
                onUpdateSettings({ ...renderSettings, title: e.target.value })
              }
            />
          </div>

          {/* Description */}
          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              rows={4}
              placeholder="They really said that... #shorts"
              value={renderSettings.description}
              onChange={e =>
                onUpdateSettings({ ...renderSettings, description: e.target.value })
              }
            />
          </div>

          {/* Catalog Starting Page (Auto-Scout) */}
          {isAuto && (
            <div className="form-group">
              <label className="form-label">Starting Catalog Page Configuration</label>
              <div className="flex-center gap-1">
                <input
                  type="number"
                  min="0"
                  max="10"
                  placeholder="Page (0-10)"
                  value={renderSettings.startPage}
                  onChange={e =>
                    onUpdateSettings({ ...renderSettings, startPage: parseInt(e.target.value) || 0 })
                  }
                  disabled={renderSettings.randomPage}
                  style={{ flex: 1 }}
                />
                <label className="toggle-switch" title="Pick a random Thread Page layout randomly on execution." style={{ marginLeft: '1rem' }}>
                  <span className="text-secondary" style={{ marginRight: '0.4rem', fontSize: '0.85rem' }}>Random</span>
                  <input
                    type="checkbox"
                    checked={renderSettings.randomPage}
                    onChange={e =>
                      onUpdateSettings({ ...renderSettings, randomPage: e.target.checked })
                    }
                  />
                  <span className="slider"></span>
                </label>
              </div>
            </div>
          )}

          {/* TTS Voice Selection */}
          <div className="form-group">
            <label className="form-label">
              <Mic size={16} /> Narrator Voice
            </label>
            <select
              value={renderSettings.ttsVoice}
              onChange={e =>
                onUpdateSettings({ ...renderSettings, ttsVoice: e.target.value })
              }
            >
              {voices.length > 0 ? (
                voices.map(v => (
                  <option key={v.name} value={v.name}>
                    {formatVoiceName(v)}
                  </option>
                ))
              ) : (
                <option value={renderSettings.ttsVoice}>
                  {renderSettings.ttsVoice} (loading...)
                </option>
              )}
            </select>
          </div>

          {/* TTS Speed Control */}
          <div className="form-group">
            <div className="rate-control">
              <label className="form-label form-label-row">
                <Volume2 size={16} />
                Narration Speed
                <span className="rate-badge">
                  {formatRate(renderSettings.ttsRate)}
                </span>
              </label>
              <input
                type="range"
                min={-50}
                max={100}
                step={5}
                value={renderSettings.ttsRate}
                onChange={e =>
                  onUpdateSettings({
                    ...renderSettings,
                    ttsRate: parseInt(e.target.value),
                  })
                }
              />
              <div className="rate-labels">
                <span>Slower</span>
                <span>Default</span>
                <span>Faster</span>
              </div>
            </div>
          </div>

          {/* Background Music */}
          <div className="form-group">
            <label className="form-label">
              <Music size={16} /> Background Music
            </label>
            <select
              value={renderSettings.musicFile}
              onChange={e =>
                onUpdateSettings({ ...renderSettings, musicFile: e.target.value })
              }
            >
              <option value="">None (no music)</option>
              {musicTracks.map(t => (
                <option key={t.file} value={t.file}>
                  🎵 {t.name}
                </option>
              ))}
            </select>
          </div>

          {/* Music Volume (only shown if a track is selected) */}
          {renderSettings.musicFile && (
            <div className="form-group">
              <div className="rate-control">
                <label className="form-label form-label-row">
                  <Volume2 size={16} />
                  Music Volume
                  <span className="rate-badge" style={{ background: 'linear-gradient(135deg, #7c3aed, #a855f7)' }}>
                    {Math.round(renderSettings.musicVolume * 100)}%
                  </span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={Math.round(renderSettings.musicVolume * 100)}
                  onChange={e =>
                    onUpdateSettings({
                      ...renderSettings,
                      musicVolume: parseInt(e.target.value) / 100,
                    })
                  }
                />
                <div className="rate-labels">
                  <span>Silent</span>
                  <span>Subtle</span>
                  <span>Loud</span>
                </div>
              </div>
            </div>
          )}

          {/* YouTube Upload Toggle */}
          <div className="toggle-row">
            <div className="flex-center gap-1">
              <Youtube color="#ff0000" size={22} />
              <span style={{ fontWeight: '600' }}>Auto-Upload to YouTube</span>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={renderSettings.uploadToYoutube}
                onChange={e =>
                  onUpdateSettings({
                    ...renderSettings,
                    uploadToYoutube: e.target.checked,
                  })
                }
              />
              <span className="slider"></span>
            </label>
          </div>

          {/* Ken Burns Toggle */}
          <div className="toggle-row" style={{marginTop: '0.5rem'}}>
            <div className="flex-center gap-1">
              <span style={{ fontWeight: '600' }}>Dynamic Camera (Ken Burns)</span>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={renderSettings.ken_burns || false}
                onChange={e =>
                  onUpdateSettings({
                    ...renderSettings,
                    ken_burns: e.target.checked,
                  })
                }
              />
              <span className="slider"></span>
            </label>
          </div>

          {/* Action Buttons */}
          <div className="render-actions">
            <button className="btn-secondary" onClick={onBack}>
              Back
            </button>
            <button className="btn-primary" onClick={onStartRender} disabled={loading}>
              {isAuto ? (
                <>
                  <Zap size={18} /> Start Automation
                </>
              ) : (
                <>
                  <MonitorPlay size={18} /> Start Render
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
