import React, { useState, useEffect } from 'react';
import { Plus, Trash2, RefreshCw, Folder, Play, CheckCircle2, AlertTriangle, Cpu } from 'lucide-react';
import { createProject, deleteProject, startIngestion, getIngestionProgressUrl } from '../utils/api';

export default function Projects({ projects, loadProjects, activeProject, setActiveProject }) {
  const [name, setName] = useState('');
  const [sourcePath, setSourcePath] = useState('');
  const [description, setDescription] = useState('');
  
  const [formError, setFormError] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Track active ingestion logs/progress by project ID
  const [ingestionLogs, setIngestionLogs] = useState({});

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name || !sourcePath) return;

    setLoading(true);
    setFormError('');
    try {
      const newProj = await createProject(name, sourcePath, description);
      setName('');
      setSourcePath('');
      setDescription('');
      await loadProjects();
    } catch (err) {
      setFormError(err.message || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this project? This will remove all chunks and memory context.')) return;

    try {
      await deleteProject(id);
      if (activeProject?.id === id) {
        setActiveProject(null);
      }
      await loadProjects();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleIngest = async (id, e) => {
    e.stopPropagation();
    try {
      await startIngestion(id);
      loadProjects(); // Update active ingesting status
      listenToProgress(id);
    } catch (err) {
      alert(`Failed to start ingestion: ${err.message}`);
    }
  };

  const listenToProgress = (id) => {
    const sseUrl = getIngestionProgressUrl(id);
    const eventSource = new EventSource(sseUrl);

    setIngestionLogs(prev => ({
      ...prev,
      [id]: { phase: 'starting', message: 'Initiating backend ingestion task...', logs: [] }
    }));

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      setIngestionLogs(prev => {
        const current = prev[id] || { logs: [] };
        const updatedLogs = [...(current.logs || []), data.message];
        
        return {
          ...prev,
          [id]: {
            phase: data.phase,
            message: data.message,
            files_processed: data.files_processed,
            chunks_created: data.chunks_created,
            current_batch: data.current_batch,
            total_batches: data.total_batches,
            summary: data.summary,
            logs: updatedLogs.slice(-10) // Keep last 10 log messages
          }
        };
      });

      if (data.phase === 'completed' || data.phase === 'error') {
        eventSource.close();
        loadProjects(); // Refresh metadata after done
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setIngestionLogs(prev => ({
        ...prev,
        [id]: { ...prev[id], phase: 'error', message: 'SSE progress connection disconnected.' }
      }));
      loadProjects();
    };
  };

  // Re-connect SSE progress listeners for any project marked is_ingesting on mount
  useEffect(() => {
    projects.forEach(p => {
      if (p.is_ingesting && !ingestionLogs[p.id]) {
        listenToProgress(p.id);
      }
    });
  }, [projects]);

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Project Management</h1>
          <p className="page-subtitle">Index repositories, configure source paths, and monitor ingestion progress.</p>
        </div>
      </div>

      <div className="projects-layout">
        {/* Creation Form */}
        <div className="project-form-panel glass-panel">
          <h3>Create New Project</h3>
          <form onSubmit={handleCreate}>
            <div className="form-group">
              <label>Project Name</label>
              <input 
                type="text" 
                placeholder="e.g. Flask Web Framework"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            
            <div className="form-group">
              <label>Source Repository (Local Path or GitHub URL)</label>
              <input 
                type="text" 
                placeholder="e.g. D:/Projects/flask or https://github.com/pallets/flask"
                value={sourcePath}
                onChange={(e) => setSourcePath(e.target.value)}
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label>Description</label>
              <textarea 
                placeholder="Brief description of this codebase"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={loading}
              />
            </div>

            {formError && <div className="form-error-alert">{formError}</div>}

            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <RefreshCw className="spin" size={16} /> : <Plus size={16} />}
              <span>Create Project</span>
            </button>
          </form>
        </div>

        {/* Projects list */}
        <div className="projects-list-panel">
          <h3>Active Projects</h3>
          {projects.length === 0 ? (
            <div className="projects-empty glass-panel">
              <Folder size={48} className="empty-icon" />
              <p>No projects configured. Use the form to index your first codebase.</p>
            </div>
          ) : (
            <div className="projects-grid">
              {projects.map(p => {
                const currentIngest = ingestionLogs[p.id];
                const isIngesting = p.is_ingesting || currentIngest?.phase === 'parsing' || currentIngest?.phase === 'embedding';

                return (
                  <div 
                    key={p.id} 
                    className={`project-card glass-panel ${activeProject?.id === p.id ? 'active' : ''}`}
                    onClick={() => !isIngesting && setActiveProject(p)}
                  >
                    <div className="project-card-header">
                      <div className="project-title-area">
                        <Folder size={20} className="folder-icon" />
                        <h4>{p.name}</h4>
                      </div>
                      <div className="project-actions">
                        <button 
                          className="action-btn delete" 
                          onClick={(e) => handleDelete(p.id, e)}
                          disabled={isIngesting}
                          title="Delete Project"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>

                    <p className="project-desc">{p.description || 'No description provided.'}</p>
                    
                    <div className="project-meta-row">
                      <span>Files: <strong>{p.file_count}</strong></span>
                      <span>Chunks: <strong>{p.chunk_count}</strong></span>
                    </div>

                    <div className="project-path-row" title={p.source_path}>
                      Source: <code>{p.source_path}</code>
                    </div>

                    {/* Progress Bar Area */}
                    {currentIngest && (
                      <div className="project-ingestion-progress">
                        <div className="progress-status-row">
                          <span className="status-phase">
                            <Cpu size={12} className="spin" />
                            {currentIngest.phase.toUpperCase()}:
                          </span>
                          <span className="status-message">{currentIngest.message}</span>
                        </div>
                        {currentIngest.total_batches > 0 && (
                          <div className="progress-bar-container">
                            <div 
                              className="progress-bar-fill"
                              style={{ width: `${(currentIngest.current_batch / currentIngest.total_batches) * 100}%` }}
                            ></div>
                          </div>
                        )}
                        
                        {currentIngest.summary && (
                          <div className="progress-summary">
                            <div>Stored Chunks: <strong>{currentIngest.summary.chunks_stored}</strong></div>
                            <div>Unchanged Files: <strong>{currentIngest.summary.unchanged_files}</strong></div>
                          </div>
                        )}
                      </div>
                    )}

                    {!isIngesting && (
                      <button 
                        className="btn btn-secondary btn-ingest" 
                        onClick={(e) => handleIngest(p.id, e)}
                      >
                        <Play size={14} />
                        <span>{p.last_ingestion ? 'Re-Ingest Codebase' : 'Ingest Codebase'}</span>
                      </button>
                    )}

                    {isIngesting && !currentIngest && (
                      <div className="project-ingestion-waiting">
                        <RefreshCw className="spin" size={14} />
                        <span>Background Ingestion active...</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
