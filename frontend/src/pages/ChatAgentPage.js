import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, MessageSquare, Send, Loader2, AlertCircle, Plus, Table, Code, RefreshCw } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function ChatAgentPage() {
  const { agentId } = useParams();
  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // CA State
  const [caAgents, setCaAgents] = useState([]);
  const [selectedCaAgent, setSelectedCaAgent] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [caLoading, setCaLoading] = useState(false);
  const [caError, setCaError] = useState(null);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    loadAgent();
  }, [agentId]);

  useEffect(() => {
    if (agent) {
      loadCaAgents();
    }
  }, [agent]);

  useEffect(() => {
    // Scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadAgent = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/agents/${agentId}`, {
        withCredentials: true
      });
      setAgent(response.data);
    } catch (error) {
      console.error('Failed to load agent:', error);
      setError('Failed to load agent');
    } finally {
      setLoading(false);
    }
  };

  const loadCaAgents = async () => {
    setCaLoading(true);
    setCaError(null);
    try {
      const response = await axios.get(`${BACKEND_URL}/api/ca/agents`, {
        withCredentials: true
      });
      setCaAgents(response.data.agents || []);
      
      // Auto-select first agent
      if (response.data.agents && response.data.agents.length > 0) {
        setSelectedCaAgent(response.data.agents[0]);
        loadConversations(response.data.agents[0].name);
      }
    } catch (error) {
      console.error('Failed to load CA agents:', error);
      setCaError(error.response?.data?.detail || 'Failed to load data agents. Please check GCP configuration.');
    } finally {
      setCaLoading(false);
    }
  };

  const loadConversations = async (agentName) => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/ca/agents/${encodeURIComponent(agentName)}/conversations`,
        { withCredentials: true }
      );
      setConversations(response.data.conversations || []);
      
      // Auto-select first conversation or create new one
      if (response.data.conversations && response.data.conversations.length > 0) {
        setCurrentConversation(response.data.conversations[0]);
        loadMessages(response.data.conversations[0].name);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadMessages = async (conversationName) => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/ca/conversations/${encodeURIComponent(conversationName)}/messages`,
        { withCredentials: true }
      );
      setMessages(response.data.messages || []);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const createNewConversation = async () => {
    if (!selectedCaAgent) return;
    
    setCaLoading(true);
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/ca/agents/${encodeURIComponent(selectedCaAgent.name)}/conversations`,
        {},
        { withCredentials: true }
      );
      
      const newConvo = response.data;
      setConversations([newConvo, ...conversations]);
      setCurrentConversation(newConvo);
      setMessages([]);
      inputRef.current?.focus();
    } catch (error) {
      console.error('Failed to create conversation:', error);
      setCaError('Failed to create new conversation');
    } finally {
      setCaLoading(false);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || !currentConversation || sending) return;
    
    const messageText = inputMessage.trim();
    setInputMessage('');
    setSending(true);
    
    // Add user message to UI immediately
    const userMessage = {
      author: 'user',
      content: { text: messageText },
      create_time: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);
    
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/ca/conversations/${encodeURIComponent(currentConversation.name)}/messages`,
        { message: messageText },
        { withCredentials: true }
      );
      
      // Add AI response
      const aiResponse = response.data.response;
      const aiMessage = {
        author: 'assistant',
        content: aiResponse,
        create_time: new Date().toISOString()
      };
      setMessages(prev => [...prev, aiMessage]);
      
    } catch (error) {
      console.error('Failed to send message:', error);
      // Add error message
      setMessages(prev => [...prev, {
        author: 'system',
        content: { text: 'Failed to get response. Please try again.' },
        create_time: new Date().toISOString(),
        isError: true
      }]);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const selectCaAgent = (caAgent) => {
    setSelectedCaAgent(caAgent);
    setCurrentConversation(null);
    setMessages([]);
    loadConversations(caAgent.name);
  };

  const selectConversation = (convo) => {
    setCurrentConversation(convo);
    loadMessages(convo.name);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Error Loading Agent</h2>
          <p className="text-slate-400 mb-4">{error || 'Agent not found'}</p>
          <Link to="/dashboard" className="text-cyan-400 hover:underline">
            Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-4 py-3 flex-shrink-0">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </Link>
            <div className="h-6 w-px bg-slate-700"></div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-cyan-500/20 rounded-lg flex items-center justify-center">
                <MessageSquare className="w-4 h-4 text-cyan-400" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                  {agent.name}
                </h1>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {agent.tag && (
              <span className="text-xs font-medium px-2 py-1 rounded-md bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                {agent.tag}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden">
        {/* Sidebar - Agent & Conversation List */}
        <div className="w-64 bg-slate-850 border-r border-slate-700 flex flex-col flex-shrink-0" style={{ backgroundColor: '#1a1f2e' }}>
          {/* Data Agent Selector */}
          <div className="p-4 border-b border-slate-700">
            <label className="text-xs text-slate-500 mb-2 block">Data Agent</label>
            <select
              value={selectedCaAgent?.name || ''}
              onChange={(e) => {
                const agent = caAgents.find(a => a.name === e.target.value);
                if (agent) selectCaAgent(agent);
              }}
              className="w-full bg-slate-800 border border-slate-600 text-white text-sm rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              disabled={caLoading || caAgents.length === 0}
            >
              {caAgents.length === 0 && <option value="">No agents available</option>}
              {caAgents.map((agent) => (
                <option key={agent.name} value={agent.name}>
                  {agent.display_name || agent.name.split('/').pop()}
                </option>
              ))}
            </select>
          </div>
          
          {/* Conversations */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-slate-500">Conversations</span>
                <button
                  onClick={createNewConversation}
                  disabled={!selectedCaAgent || caLoading}
                  className="text-cyan-400 hover:text-cyan-300 disabled:text-slate-600"
                  title="New conversation"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
              
              {conversations.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-4">
                  No conversations yet
                </p>
              ) : (
                <div className="space-y-1">
                  {conversations.map((convo, idx) => (
                    <button
                      key={convo.name}
                      onClick={() => selectConversation(convo)}
                      className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                        currentConversation?.name === convo.name
                          ? 'bg-cyan-500/20 text-cyan-400'
                          : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                      }`}
                    >
                      Chat {conversations.length - idx}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {caError ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center max-w-md px-6">
                <AlertCircle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-white mb-3">Configuration Required</h2>
                <p className="text-slate-400 mb-4">{caError}</p>
                <p className="text-sm text-slate-500 mb-4">
                  Please ensure GCP_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS are configured in the backend.
                </p>
                <button
                  onClick={loadCaAgents}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-md hover:bg-slate-700"
                >
                  <RefreshCw className="w-4 h-4" />
                  Retry
                </button>
              </div>
            </div>
          ) : !currentConversation ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <MessageSquare className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-white mb-2">Start a Conversation</h2>
                <p className="text-slate-400 mb-4">
                  {selectedCaAgent 
                    ? 'Click the + button to start a new conversation'
                    : 'Select a data agent to begin'}
                </p>
                {selectedCaAgent && (
                  <button
                    onClick={createNewConversation}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-md hover:bg-cyan-700"
                  >
                    <Plus className="w-4 h-4" />
                    New Conversation
                  </button>
                )}
              </div>
            </div>
          ) : (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 && (
                  <div className="text-center py-8">
                    <p className="text-slate-500">Ask a question about your data</p>
                  </div>
                )}
                
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.author === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-3xl rounded-lg p-4 ${
                        msg.author === 'user'
                          ? 'bg-cyan-600 text-white'
                          : msg.isError
                          ? 'bg-red-900/50 text-red-200 border border-red-800'
                          : 'bg-slate-800 text-white'
                      }`}
                    >
                      {/* Text content */}
                      {msg.content?.text && (
                        <p className="whitespace-pre-wrap">{msg.content.text}</p>
                      )}
                      
                      {/* SQL content */}
                      {msg.content?.sql && (
                        <div className="mt-3">
                          <div className="flex items-center gap-2 text-xs text-slate-400 mb-2">
                            <Code className="w-3 h-3" />
                            Generated SQL
                          </div>
                          <pre className="bg-slate-900 p-3 rounded text-sm overflow-x-auto text-green-400">
                            {msg.content.sql}
                          </pre>
                        </div>
                      )}
                      
                      {/* Table content */}
                      {msg.content?.table && msg.content.table.rows?.length > 0 && (
                        <div className="mt-3">
                          <div className="flex items-center gap-2 text-xs text-slate-400 mb-2">
                            <Table className="w-3 h-3" />
                            Query Results
                          </div>
                          <div className="overflow-x-auto">
                            <table className="min-w-full text-sm">
                              <thead>
                                <tr className="border-b border-slate-700">
                                  {msg.content.table.columns?.map((col, i) => (
                                    <th key={i} className="px-3 py-2 text-left text-slate-400 font-medium">
                                      {col}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {msg.content.table.rows?.slice(0, 10).map((row, rowIdx) => (
                                  <tr key={rowIdx} className="border-b border-slate-800">
                                    {row.map((cell, cellIdx) => (
                                      <td key={cellIdx} className="px-3 py-2 text-slate-300">
                                        {cell}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                            {msg.content.table.rows?.length > 10 && (
                              <p className="text-xs text-slate-500 mt-2">
                                Showing 10 of {msg.content.table.rows.length} rows
                              </p>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                
                {sending && (
                  <div className="flex justify-start">
                    <div className="bg-slate-800 rounded-lg p-4">
                      <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="border-t border-slate-700 p-4">
                <form onSubmit={sendMessage} className="max-w-4xl mx-auto flex gap-3">
                  <input
                    ref={inputRef}
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Ask a question about your data..."
                    className="flex-1 bg-slate-800 border border-slate-600 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                    disabled={sending}
                  />
                  <button
                    type="submit"
                    disabled={!inputMessage.trim() || sending}
                    className="px-6 py-3 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:bg-slate-700 disabled:text-slate-500 transition-colors flex items-center gap-2"
                  >
                    {sending ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </button>
                </form>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
