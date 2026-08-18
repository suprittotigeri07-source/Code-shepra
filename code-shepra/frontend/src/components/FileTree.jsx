import React, { useState, useMemo } from 'react';
import { Folder, FolderOpen, FileCode, Search, ChevronRight, ChevronDown } from 'lucide-react';

// Helper to construct tree from flat paths
function buildTree(files) {
  const root = { name: 'Root', isDirectory: true, children: {}, path: '' };
  
  files.forEach(file => {
    const parts = file.file_path.split('/');
    let current = root;
    let currentPath = '';
    
    parts.forEach((part, index) => {
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isLast = index === parts.length - 1;
      
      if (!current.children[part]) {
        current.children[part] = {
          name: part,
          isDirectory: isLast ? file.is_directory : true,
          path: currentPath,
          language: isLast ? file.language : '',
          children: {}
        };
      }
      current = current.children[part];
    });
  });
  
  return root;
}

// Tree node component
function TreeNode({ node, onFileClick, activeFile, depth }) {
  const [isOpen, setIsOpen] = useState(depth === 0); // Open root by default
  const isDir = node.isDirectory;
  
  const hasChildren = Object.keys(node.children).length > 0;
  
  const sortedChildren = useMemo(() => {
    return Object.values(node.children).sort((a, b) => {
      if (a.isDirectory && !b.isDirectory) return -1;
      if (!a.isDirectory && b.isDirectory) return 1;
      return a.name.localeCompare(b.name);
    });
  }, [node.children]);

  const handleClick = (e) => {
    e.stopPropagation();
    if (isDir) {
      setIsOpen(!isOpen);
    } else {
      onFileClick(node.path);
    }
  };

  return (
    <div style={{ marginLeft: depth > 0 ? '12px' : '0' }}>
      {depth > 0 && (
        <div 
          className={`file-tree-node ${activeFile === node.path ? 'active' : ''}`}
          onClick={handleClick}
        >
          {isDir ? (
            <>
              {isOpen ? <ChevronDown size={14} className="tree-arrow" /> : <ChevronRight size={14} className="tree-arrow" />}
              {isOpen ? <FolderOpen size={16} className="folder-icon open" /> : <Folder size={16} className="folder-icon" />}
            </>
          ) : (
            <FileCode size={16} className="file-icon" />
          )}
          <span className="node-name">{node.name}</span>
        </div>
      )}
      
      {isDir && (isOpen || depth === 0) && (
        <div className="node-children">
          {sortedChildren.map(child => (
            <TreeNode 
              key={child.path} 
              node={child} 
              onFileClick={onFileClick} 
              activeFile={activeFile}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function FileTree({ files, onFileClick, activeFile }) {
  const [search, setSearch] = useState('');
  
  // Filter files based on search string
  const filteredFiles = useMemo(() => {
    if (!search) return files;
    return files.filter(f => f.file_path.toLowerCase().includes(search.toLowerCase()));
  }, [files, search]);

  const tree = useMemo(() => buildTree(filteredFiles), [filteredFiles]);

  return (
    <div className="file-tree-panel">
      <div className="file-tree-search-container">
        <Search size={14} className="search-icon" />
        <input 
          type="text" 
          placeholder="Filter files..." 
          className="file-tree-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      
      <div className="file-tree-scroll">
        {files.length === 0 ? (
          <div className="empty-tree-message">No files indexed yet. Ingest this project first.</div>
        ) : (
          <TreeNode 
            node={tree} 
            onFileClick={onFileClick} 
            activeFile={activeFile}
            depth={0}
          />
        )}
      </div>
    </div>
  );
}
