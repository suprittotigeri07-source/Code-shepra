import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Sparkles, MessageSquarePlus, RefreshCw, ChevronDown, ChevronUp, FileCode } from 'lucide-react';
import { getChatUrl } from '../utils/api';

export default function ChatPanel({ activeProject, onFileClick, activeFile, setLineRange }) {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [followUpMode, setFollowUpMode] = useState(true);
  const [agentSteps, setAgentSteps] = useState([]);
  const [showSteps, setShowSteps] = useState(true);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, agentSteps]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!query.trim() || !activeProject || loading) return;

    const userMessage = { role: 'user', content: query };
    const currentQuery = query;
    
    setMessages(prev => [...prev, userMessage]);
    setQuery('');
    setLoading(true);
    setAgentSteps([]);
    
    // Setup message placeholder for assistant stream
    const assistantMessageId = Date.now();
    setMessages(prev => [...prev, { id: assistantMessageId, role: 'assistant', content: '', files_explored: [], loading: true }]);

    try {
      const historyToSend = followUpMode
        ? messages.map(m => ({ role: m.role, content: m.content }))
        : [];

      // Open SSE connection
      const response = await fetch(getChatUrl(activeProject.id), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: currentQuery, history: historyToSend })
      });

      if (!response.ok) throw new Error(await response.text());

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Save the last line if it's incomplete
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data: ')) continue;
          
          try {
            const event = JSON.parse(trimmed.slice(6));
            
            if (event.type === 'classifying') {
              setAgentSteps(prev => [...prev, { type: 'classifying', text: `Analyzing intent of: "${event.data.query}"` }]);
            } else if (event.type === 'classified') {
              setAgentSteps(prev => [...prev, { type: 'classified', text: `Classified as ${event.data.intent.toUpperCase()} intent (${event.data.reasoning})` }]);
            } else if (event.type === 'thinking') {
              setAgentSteps(prev => [...prev, { type: 'thinking', text: `Thinking (Iteration ${event.data.step})...` }]);
            } else if (event.type === 'tool_call') {
              const argsStr = JSON.stringify(event.data.args);
              setAgentSteps(prev => [...prev, { type: 'tool_call', text: `🔧 Invoking: ${event.data.tool}(${argsStr.slice(0, 80)}${argsStr.length > 80 ? '...' : ''})` }]);
            } else if (event.type === 'tool_result') {
              setAgentSteps(prev => [...prev, { type: 'tool_result', text: `✅ Result: ${event.data.summary}` }]);
            } else if (event.type === 'response') {
              setMessages(prev => prev.map(m => {
                if (m.id === assistantMessageId) {
                  return {
                    ...m,
                    content: event.data.content,
                    files_explored: event.data.files_explored || [],
                    loading: false
                  };
                }
                return m;
              }));
            }
          } catch (e) {
            console.error('Failed to parse SSE line:', line, e);
          }
        }
      }
    } catch (err) {
      console.error('Chat error:', err);
      setMessages(prev => prev.map(m => {
        if (m.id === assistantMessageId) {
          return {
            ...m,
            content: `⚠️ Error generating response: ${err.message}`,
            loading: false
          };
        }
        return m;
      }));
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setAgentSteps([]);
    setLoading(false);
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-header-title">
          <Sparkles size={16} className="sparkles-icon" />
          <span>Semantic Explorer</span>
        </div>
        
        <div className="chat-header-actions">
          <label className="followup-toggle">
            <input 
              type="checkbox" 
              checked={followUpMode}
              onChange={(e) => setFollowUpMode(e.target.checked)}
            />
            <span>Follow-up Mode</span>
          </label>
          
          <button className="new-chat-btn" onClick={handleNewChat}>
            <MessageSquarePlus size={16} />
            <span>New Chat</span>
          </button>
        </div>
      </div>

      <div className="chat-messages-container">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <Sparkles size={48} className="welcome-icon" />
            <h3>Welcome to Code Sherpa</h3>
            <p>Ask natural language questions about your codebase, trace functions, discover dependencies, or generate project maps.</p>
            <div className="welcome-suggestions">
              <button onClick={() => setQuery("give me a map of the project structure")}>🗺️ Show me a project map</button>
              <button onClick={() => setQuery("how does database connection work?")}>🔌 How is database configured?</button>
              <button onClick={() => setQuery("where are key error handlers?")}>🚨 Where are error handlers?</button>
            </div>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((msg, i) => (
              <div key={msg.id || i} className={`message-bubble ${msg.role}`}>
                <div className="message-header">
                  {msg.role === 'user' ? 'Developer' : 'Code Sherpa'}
                </div>
                
                <div className="message-content">
                  {msg.loading ? (
                    <div className="chat-loading-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  ) : (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  )}
                </div>

                {msg.files_explored && msg.files_explored.length > 0 && (
                  <div className="message-citations">
                    <span className="citations-label">Sources explored:</span>
                    <div className="citations-list">
                      {msg.files_explored.map((file, idx) => (
                        <button 
                          key={idx} 
                          className={`citation-tag ${activeFile === file ? 'active' : ''}`}
                          onClick={() => onFileClick(file)}
                        >
                          <FileCode size={12} />
                          <span>{file.split('/').pop()}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
            
            {loading && agentSteps.length > 0 && (
              <div className="agent-steps-container glass-panel">
                <div className="agent-steps-header" onClick={() => setShowSteps(!showSteps)}>
                  <span>Agent Execution Chain</span>
                  {showSteps ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </div>
                
                {showSteps && (
                  <div className="agent-steps-list">
                    {agentSteps.map((step, idx) => (
                      <div key={idx} className={`agent-step ${step.type}`}>
                        {step.text}
                      </div>
                    ))}
                    <div className="agent-step thinking active">
                      Running analysis loop...
                    </div>
                  </div>
                )}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <form className="chat-input-container" onSubmit={handleSend}>
        <input 
          type="text" 
          placeholder={activeProject ? "Ask a question about the code..." : "Select a project to start exploring..."}
          className="chat-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={!activeProject || loading}
        />
        <button 
          type="submit" 
          className="chat-send-btn"
          disabled={!query.trim() || !activeProject || loading}
        >
          {loading ? <RefreshCw className="spin" size={16} /> : <Send size={16} />}
        </button>
      </form>
    </div>
  );
}
