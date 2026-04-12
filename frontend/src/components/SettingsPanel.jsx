import React, { useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { Settings, Save, Server, Loader2 } from 'lucide-react';

export default function SettingsPanel({ onBack }) {
  const [config, setConfig] = useState(null);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [confRes, modRes] = await Promise.all([
        axios.get('http://localhost:8000/api/config'),
        axios.get('http://localhost:8000/api/models')
      ]);
      setConfig(confRes.data);
      setModels(modRes.data.models || []);
    } catch (err) {
      toast.error('Failed to load settings from server');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type } = e.target;
    let parsedValue = value;
    if (type === 'number') parsedValue = parseFloat(value);
    
    setConfig(prev => ({
      ...prev,
      [name]: parsedValue
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.put('http://localhost:8000/api/config', config);
      toast.success('Settings saved successfully!');
      onBack();
    } catch (err) {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading || !config) {
    return (
      <div className="step-container narrow flex-center animate-fade-in">
        <Loader2 className="animate-spin" size={32} color="var(--accent-primary)" />
      </div>
    );
  }

  return (
    <div className="step-container narrow animate-fade-in">
      <div className="glass-card">
        <div className="panel-header" style={{ background: 'transparent', padding: '0 0 1rem 0' }}>
          <div className="flex-center gap-1">
            <Settings size={22} color="var(--accent-primary)" />
            <h2 className="text-gradient">Application Settings</h2>
          </div>
        </div>

        <div className="form-stack">
          {/* LLM Provider */}
          <div className="form-group">
            <label className="form-label">
              <Server size={16} /> LLM Provider
            </label>
            <select
              name="llm_provider"
              value={config.llm_provider || 'ollama'}
              onChange={handleChange}
            >
              <option value="ollama">Ollama (Local Offline)</option>
              <option value="gemini">Gemini API (Cloud)</option>
            </select>
          </div>
          
          {config.llm_provider === 'gemini' && (
            <div className="form-group">
              <label className="form-label">Gemini API Key</label>
              <input
                type="password"
                name="gemini_api_key"
                value={config.gemini_api_key || ''}
                onChange={handleChange}
                placeholder="AIza..."
              />
            </div>
          )}

          {/* LLM Model */}
          <div className="form-group">
            <label className="form-label">
              <Server size={16} /> Ollama Model
            </label>
            <select
              name="llm_model"
              value={config.llm_model || ''}
              onChange={handleChange}
            >
              {models.length > 0 ? (
                models.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))
              ) : (
                <option value={config.llm_model}>{config.llm_model} (offline)</option>
              )}
            </select>
            <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: '4px' }}>
              Select a local model pulled via Ollama. Llama3.1 or Mistral recommended.
            </p>
          </div>

          {/* Temperature */}
          <div className="form-group">
            <label className="form-label form-label-row">
              Creativity (Temperature)
              <span className="rate-badge">{(config.llm_temperature || 0)*100}%</span>
            </label>
            <input
              type="range"
              name="llm_temperature"
              min="0"
              max="1"
              step="0.1"
              value={config.llm_temperature || 0}
              onChange={handleChange}
            />
            <div className="rate-labels">
              <span>Logical</span>
              <span>Creative</span>
            </div>
          </div>

          {/* Censor Mode */}
          <div className="form-group">
            <label className="form-label">Audio Censor Mode</label>
            <select
              name="censor_mode"
              value={config.censor_mode || 'beep'}
              onChange={handleChange}
            >
              <option value="beep">Beep (Bleeping tone overlay)</option>
              <option value="mute">Mute (Cut audio entirely)</option>
            </select>
          </div>

          {/* Video Options (Placeholder for expansion) */}
          <div className="form-group" style={{marginTop: '1rem'}}>
             <h3 style={{fontSize: '1rem', marginBottom: '0.5rem', color: 'var(--text-primary)'}}>Video Generation</h3>
          </div>

          <div className="form-group">
            <label className="form-label">Video Preset (FFmpeg)</label>
            <select
              name="video_preset"
              value={config.video_preset || 'fast'}
              onChange={handleChange}
            >
              <option value="ultrafast">Ultrafast (Draft)</option>
              <option value="fast">Fast (Standard)</option>
              <option value="medium">Medium (HQ)</option>
              <option value="slow">Slow (Max Quality)</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Framerate (FPS)</label>
            <select
              name="video_fps"
              value={config.video_fps || 30}
              onChange={handleChange}
            >
              <option value={24}>24 FPS (Cinematic)</option>
              <option value={30}>30 FPS (Standard)</option>
              <option value={60}>60 FPS (Smooth)</option>
            </select>
          </div>

          {/* Actions */}
          <div className="render-actions" style={{ marginTop: '2rem' }}>
            <button className="btn-secondary" onClick={onBack} disabled={saving}>
              Cancel
            </button>
            <button className="btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
              Save Configuration
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
