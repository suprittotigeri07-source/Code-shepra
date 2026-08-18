import React, { useEffect, useRef, useState } from 'react';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';
import { File, Download, Maximize2, Minimize2 } from 'lucide-react';

export default function CodeViewer({ filePath, fileContent, loading }) {
  const codeRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (codeRef.current && fileContent) {
      hljs.highlightElement(codeRef.current);
    }
  }, [fileContent, filePath]);

  const handleDownload = () => {
    if (!fileContent) return;
    const blob = new Blob([fileContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filePath.split('/').pop() || 'file.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  const getLanguageClass = (path) => {
    const ext = path ? path.split('.').pop() : '';
    if (['js', 'jsx'].includes(ext)) return 'javascript';
    if (['ts', 'tsx'].includes(ext)) return 'typescript';
    if (['py'].includes(ext)) return 'python';
    if (['go'].includes(ext)) return 'go';
    if (['java'].includes(ext)) return 'java';
    if (['rs'].includes(ext)) return 'rust';
    if (['c', 'h'].includes(ext)) return 'c';
    if (['cpp', 'hpp', 'cc'].includes(ext)) return 'cpp';
    if (['rb'].includes(ext)) return 'ruby';
    if (['php'].includes(ext)) return 'php';
    if (['cs'].includes(ext)) return 'csharp';
    if (['swift'].includes(ext)) return 'swift';
    if (['sh', 'bash'].includes(ext)) return 'bash';
    if (['yaml', 'yml'].includes(ext)) return 'yaml';
    if (['json'].includes(ext)) return 'json';
    if (['html'].includes(ext)) return 'html';
    if (['css'].includes(ext)) return 'css';
    if (['md'].includes(ext)) return 'markdown';
    return 'plaintext';
  };

  const lineCount = fileContent ? fileContent.split('\n').length : 0;
  const lineNumbers = Array.from({ length: lineCount }, (_, i) => i + 1);

  return (
    <div className={`code-viewer-panel ${isFullscreen ? 'fullscreen' : ''}`}>
      <div className="code-viewer-header">
        <div className="file-info">
          <File size={16} className="file-icon" />
          <span className="file-path">{filePath || 'No file open'}</span>
        </div>
        
        {fileContent && (
          <div className="viewer-actions">
            <button className="viewer-btn" onClick={handleDownload} title="Download File">
              <Download size={14} />
            </button>
            <button 
              className="viewer-btn" 
              onClick={() => setIsFullscreen(!isFullscreen)} 
              title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
            >
              {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
          </div>
        )}
      </div>

      <div className="code-viewer-container">
        {loading ? (
          <div className="viewer-loading">
            <div className="spinner"></div>
            <span>Reading file...</span>
          </div>
        ) : !fileContent ? (
          <div className="viewer-placeholder">
            <File size={48} className="placeholder-icon" />
            <p>Select a file from the explorer or click a source in the chat to view code content.</p>
          </div>
        ) : (
          <div className="code-scroll-container">
            <div className="line-numbers">
              {lineNumbers.map(n => (
                <div key={n} className="line-number-cell">{n}</div>
              ))}
            </div>
            
            <pre className="code-block">
              <code 
                ref={codeRef} 
                className={`language-${getLanguageClass(filePath)}`}
              >
                {fileContent}
              </code>
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
