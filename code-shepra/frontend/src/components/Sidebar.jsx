import React from 'react';
import { Compass, FolderCode, BrainCircuit, Terminal } from 'lucide-react';

export default function Sidebar({ currentPage, setCurrentPage, projects, activeProject, setActiveProject }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <Terminal className="logo-icon" size={24} />
        <span className="logo-text">Code Sherpa</span>
      </div>
      
      <nav className="sidebar-nav">
        <button 
          className={`nav-item ${currentPage === 'explorer' ? 'active' : ''}`}
          onClick={() => setCurrentPage('explorer')}
        >
          <Compass size={18} />
          <span>Explorer</span>
        </button>
        
        <button 
          className={`nav-item ${currentPage === 'projects' ? 'active' : ''}`}
          onClick={() => setCurrentPage('projects')}
        >
          <FolderCode size={18} />
          <span>Projects</span>
        </button>
        
        <button 
          className={`nav-item ${currentPage === 'memory' ? 'active' : ''}`}
          onClick={() => setCurrentPage('memory')}
        >
          <BrainCircuit size={18} />
          <span>Memory</span>
        </button>
      </nav>
      
      <div className="sidebar-project-selector">
        <span className="project-select-label">Active Project</span>
        <select 
          className="project-dropdown"
          value={activeProject?.id || ''}
          onChange={(e) => {
            const proj = projects.find(p => p.id === parseInt(e.target.value));
            setActiveProject(proj || null);
          }}
          disabled={projects.length === 0}
        >
          {projects.length === 0 ? (
            <option value="">No projects created</option>
          ) : (
            <>
              <option value="">Select a project...</option>
              {projects.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} {p.is_ingesting ? '🔄' : ''}
                </option>
              ))}
            </>
          )}
        </select>
      </div>
    </aside>
  );
}
