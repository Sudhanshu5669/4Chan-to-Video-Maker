import React from 'react';
import { Terminal, Loader2 } from 'lucide-react';

export default function StreamTerminal({
  visible,
  streamingStatus,
  streamingText,
  terminalRef,
}) {
  if (!visible) return null;

  return (
    <div className="stream-terminal" ref={terminalRef}>
      <div className="stream-terminal-header">
        <Terminal size={14} />
        {streamingStatus}
        <Loader2 size={14} className="animate-spin" style={{ marginLeft: 'auto' }} />
      </div>
      <div className="stream-content">
        {streamingText}
        <span className="stream-cursor" />
      </div>
    </div>
  );
}
