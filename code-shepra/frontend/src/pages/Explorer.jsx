import React, { useState, useEffect } from 'react';
import FileTree from '../components/FileTree';
import ChatPanel from '../components/ChatPanel';
import CodeViewer from '../components/CodeViewer';
import { fetchFileTree, fetchFileContent } from '../utils/api';
import { Sparkles, HelpCircle } from 'lucide-react';

export default function Explorer({ activeProject }) {
  const [files, setFiles] = useState([]);
  const [treeLoading, setTreeLoading] = useState(false);
  
  const [activeFile, setActiveFile] = useState(null);
  const [fileContent, setFileContent] = useState(null);
  const [contentLoading, setContentLoading] = useState(false);

  // Load file tree on project change
  useEffect(() => {
    if (!activeProject) {
      setFiles([]);
      setActiveFile(null);
      setFileContent(null);
      return;
    }

    const loadTree = async () => {
      setTreeLoading(true);
      try {
        const tree = await fetchFileTree(activeProject.id);
        setFiles(tree);
      } catch (err) {
        console.error('Failed to load file tree:', err);
      } finally {
        setTreeLoading(false);
      }
    };

    loadTree();
  }, [activeProject]);

  const handleFileClick = async (path) => {
    setActiveFile(path);
    setContentLoading(true);
    try {
      const data = await fetchFileContent(activeProject.id, path);
      setFileContent(data.content);
    } catch (err) {
      console.error('Failed to load file content:', err);
      setFileContent(`Error loading file: ${err.message}`);
    } finally {
      setContentLoading(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="explorer-page-empty">
        <div className="empty-state-card glass-panel">
          <HelpCircle size={48} className="empty-state-icon" />
          <h2>No Active Project Selected</h2>
          <p>Please select an existing project from the bottom of the sidebar, or navigate to the <strong>Projects</strong> page to create a new one.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="explorer-layout">
      {/* Panel 1: File Tree (Left) */}
      <div className="explorer-panel-tree glass-panel">
        <div className="panel-title">Repository Tree</div>
        {treeLoading ? (
          <div className="tree-loading">
            <div className="spinner"></div>
            <span>Loading tree...</span>
          </div>
        ) : (
          <FileTree 
            files={files} 
            onFileClick={handleFileClick} 
            activeFile={activeFile}
          />
        )}
      </div>

      {/* Panel 2: Chat Panel (Center) */}
      <div className="explorer-panel-chat glass-panel">
        <ChatPanel 
          activeProject={activeProject} 
          onFileClick={handleFileClick}
          activeFile={activeFile}
        />
      </div>

      {/* Panel 3: Code Viewer (Right) */}
      <div className="explorer-panel-viewer glass-panel">
        <CodeViewer 
          filePath={activeFile} 
          fileContent={fileContent} 
          loading={contentLoading}
        />
      </div>
    </div>
  );
}
