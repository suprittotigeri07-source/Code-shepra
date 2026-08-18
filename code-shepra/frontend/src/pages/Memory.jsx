import React, { useState, useEffect } from 'react';
import { Search, Brain, History, Trash2, Plus, Sparkles, AlertTriangle, FileCode, Check } from 'lucide-react';
import { 
  fetchMemory, 
  fetchExplorationSummary, 
  addSemanticMemory, 
  deleteMemory, 
  clearMemory, 
  searchMemory 
} from '../utils/api';

export default function Memory({ activeProject }) {
  const [episodicList, setEpisodicList] = useState([]);
  const [semanticList, setSemanticList] = useState([]);
  const [summary, setSummary] = useState(null);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  
  const [newContext, setNewContext] = useState('');
  const [addingContext, setAddingContext] = useState(false);

  const loadAll = async () => {
    if (!activeProject) return;
    setLoading(true);
    try {
      const data = await fetchMemory(activeProject.id);
      setEpisodicList(data.episodic || []);
      setSemanticList(data.semantic || []);
      
      const sumData = await fetchExplorationSummary(activeProject.id);
      setSummary(sumData);
    } catch (err) {
      console.error('Failed to load memories:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, [activeProject]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim() || !activeProject) {
      loadAll();
      return;
    }
    
    setLoading(true);
    try {
      const results = await searchMemory(activeProject.id, searchQuery);
      // Group results back by type
      const eps = results.filter(r => r.type === 'episodic');
      const sem = results.filter(r => r.type === 'semantic');
      setEpisodicList(eps);
      setSemanticList(sem);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddSemantic = async (e) => {
    e.preventDefault();
    if (!newContext.trim() || !activeProject) return;

    setAddingContext(true);
    try {
      await addSemanticMemory(activeProject.id, newContext);
      setNewContext('');
      await loadAll();
    } catch (err) {
      alert(`Failed to save context: ${err.message}`);
    } finally {
      setAddingContext(false);
    }
  };

  const handleDelete = async (id, type) => {
    if (!confirm(`Delete this ${type} memory entry?`)) return;
    try {
      await deleteMemory(activeProject.id, id, type);
      await loadAll();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleBulkClear = async (type) => {
    if (!confirm(`Are you sure you want to clear ALL ${type} memories for this project? This cannot be undone.`)) return;
    try {
      await clearMemory(activeProject.id, type);
      await loadAll();
    } catch (err) {
      alert(`Clear failed: ${err.message}`);
    }
  };

  if (!activeProject) {
    return (
      <div className="explorer-page-empty">
        <div className="empty-state-card glass-panel">
          <Brain size={48} className="empty-state-icon" />
          <h2>No Active Project</h2>
          <p>Select a project from the sidebar to manage exploration memory.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container scrollable">
      <div className="page-header">
        <div>
          <h1 className="page-title">Agent Memory & Context</h1>
          <p className="page-subtitle">Manage project-level context, developer assertions, and review explored files list.</p>
        </div>
      </div>

      {/* Exploration Statistics Bar */}
      {summary && (
        <div className="memory-summary-bar glass-panel">
          <div className="summary-stat-cell">
            <span className="stat-label">Exploration Progress</span>
            <div className="progress-row">
              <div className="progress-track">
                <div 
                  className="progress-fill-bar"
                  style={{ width: `${summary.exploration_percentage}%` }}
                ></div>
              </div>
              <span className="stat-val">{summary.exploration_percentage}%</span>
            </div>
          </div>
          
          <div className="summary-stat-cell small">
            <span className="stat-label">Explored Files</span>
            <span className="stat-val-text">{summary.explored_files} / {summary.total_files}</span>
          </div>

          <div className="summary-stat-cell small">
            <span className="stat-label">Queries In Session</span>
            <span className="stat-val-text">{summary.total_queries}</span>
          </div>
        </div>
      )}

      {/* Search Header */}
      <form className="memory-search-bar" onSubmit={handleSearch}>
        <div className="search-input-wrapper">
          <Search size={16} className="search-icon" />
          <input 
            type="text" 
            placeholder="Search queries, explored file targets or developer contexts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={loading}>Search</button>
        {searchQuery && (
          <button 
            type="button" 
            className="btn btn-secondary"
            onClick={() => { setSearchQuery(''); loadAll(); }}
          >
            Clear Search
          </button>
        )}
      </form>

      <div className="memory-layout">
        {/* Left Side: Semantic Context Assertions */}
        <div className="memory-column">
          <div className="column-header-row">
            <div className="column-title">
              <Brain size={18} className="icon-cyan" />
              <h3>Semantic Context Notes</h3>
            </div>
            {semanticList.length > 0 && (
              <button className="clear-all-btn" onClick={() => handleBulkClear('semantic')}>
                Clear All
              </button>
            )}
          </div>

          {/* Add Semantic Memory Form */}
          <form className="add-memory-card glass-panel" onSubmit={handleAddSemantic}>
            <textarea 
              placeholder="Inject developer context (e.g. 'the auth module handles OAuth tokens', 'avoid refactoring legacy utils')"
              value={newContext}
              onChange={(e) => setNewContext(e.target.value)}
              required
              disabled={addingContext}
            />
            <button type="submit" className="btn btn-primary btn-sm" disabled={addingContext || !newContext.trim()}>
              <Plus size={14} />
              <span>Add Asserted Context</span>
            </button>
          </form>

          {/* Semantic Entries List */}
          <div className="memory-entries-list">
            {semanticList.length === 0 ? (
              <div className="empty-list-card glass-panel">
                <Brain size={24} className="empty-icon" />
                <p>No semantic contexts configured. Add details above to guide LLM responses.</p>
              </div>
            ) : (
              semanticList.map(item => (
                <div key={item.id} className="memory-card glass-panel semantic">
                  <div className="memory-card-header">
                    <span className="timestamp">Added {new Date(item.created_at).toLocaleDateString()}</span>
                    <button className="delete-btn" onClick={() => handleDelete(item.id, 'semantic')}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <p className="memory-card-content">{item.content}</p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Side: Episodic Memory history */}
        <div className="memory-column">
          <div className="column-header-row">
            <div className="column-title">
              <History size={18} className="icon-purple" />
              <h3>Episodic History</h3>
            </div>
            {episodicList.length > 0 && (
              <button className="clear-all-btn" onClick={() => handleBulkClear('episodic')}>
                Clear All
              </button>
            )}
          </div>

          <div className="memory-entries-list">
            {episodicList.length === 0 ? (
              <div className="empty-list-card glass-panel">
                <History size={24} className="empty-icon" />
                <p>No exploration history. Start querying the chatbot on the Explorer tab.</p>
              </div>
            ) : (
              episodicList.map(item => (
                <div key={item.id} className="memory-card glass-panel episodic">
                  <div className="memory-card-header">
                    <span className="timestamp">Explored {new Date(item.created_at).toLocaleDateString()}</span>
                    <button className="delete-btn" onClick={() => handleDelete(item.id, 'episodic')}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div className="query-row">
                    <strong>Q:</strong> {item.query}
                  </div>
                  <div className="summary-row">
                    <strong>Summary:</strong> {item.summary}
                  </div>
                  {item.files_explored && item.files_explored.length > 0 && (
                    <div className="explored-files-list">
                      <FileCode size={12} />
                      {item.files_explored.map((f, idx) => (
                        <span key={idx} className="file-name">{f.split('/').pop()}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
