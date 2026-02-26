import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, MessageSquare, ExternalLink, AlertCircle, Settings } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function IframeAgentPage() {
  const { agentId } = useParams();
  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAgent();
  }, [agentId]);

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

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Error Loading Agent</h2>
          <p className="text-slate-600 mb-4">{error || 'Agent not found'}</p>
          <Link to="/dashboard" className="text-blue-600 hover:underline">
            Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  // Check if iframe URL is configured
  const hasIframeUrl = agent.iframe_url && agent.iframe_url.trim() !== '';

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-3">
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
            {hasIframeUrl && (
              <a
                href={agent.iframe_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
                Open in new tab
              </a>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 relative">
        {hasIframeUrl ? (
          <iframe
            src={agent.iframe_url}
            className="absolute inset-0 w-full h-full border-0"
            title={agent.name}
            allow="clipboard-write; clipboard-read"
            sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-modals"
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md px-6">
              <div className="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Settings className="w-8 h-8 text-slate-500" />
              </div>
              <h2 className="text-2xl font-semibold text-white mb-3" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Configuration Required
              </h2>
              <p className="text-slate-400 mb-6 leading-relaxed">
                This agent needs to be configured with an iframe URL. Please contact your administrator to set up the BigQuery Conversational Analytics endpoint.
              </p>
              <div className="bg-slate-800 rounded-lg p-4 text-left">
                <p className="text-xs text-slate-500 mb-2">Agent ID:</p>
                <code className="text-sm text-cyan-400 font-mono">{agent.agent_id}</code>
              </div>
              <div className="mt-6">
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-md hover:bg-slate-700 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Return to Dashboard
                </Link>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
