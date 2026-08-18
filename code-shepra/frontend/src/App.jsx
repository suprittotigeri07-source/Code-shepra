import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Explorer from './pages/Explorer';
import Projects from './pages/Projects';
import Memory from './pages/Memory';
import { fetchProjects } from './utils/api';
import './App.css';

export default function App() {
  const [currentPage, setCurrentPage] = useState('projects'); // Start on projects page to set up codebases
  const [projects, setProjects] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const projs = await fetchProjects();
      setProjects(projs);
      
      // Keep active project sync if it was already selected
      if (activeProject) {
        const syncProj = projs.find(p => p.id === activeProject.id);
        if (syncProj) {
          setActiveProject(syncProj);
        }
      } else if (projs.length > 0) {
        // Default to first project
        setActiveProject(projs[0]);
      }
    } catch (err) {
      console.error('Failed to fetch projects list:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const renderPage = () => {
    switch (currentPage) {
      case 'explorer':
        return <Explorer activeProject={activeProject} />;
      case 'projects':
        return (
          <Projects 
            projects={projects} 
            loadProjects={loadProjects} 
            activeProject={activeProject} 
            setActiveProject={setActiveProject} 
          />
        );
      case 'memory':
        return <Memory activeProject={activeProject} />;
      default:
        return <Projects projects={projects} loadProjects={loadProjects} activeProject={activeProject} setActiveProject={setActiveProject} />;
    }
  };

  return (
    <div className="app-container">
      <Sidebar 
        currentPage={currentPage} 
        setCurrentPage={setCurrentPage} 
        projects={projects}
        activeProject={activeProject}
        setActiveProject={setActiveProject}
      />
      <main className="main-content">
        {renderPage()}
      </main>
    </div>
  );
}
