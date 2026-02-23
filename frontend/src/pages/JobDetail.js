import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Clock, CheckCircle2, XCircle, Zap, Download, FileText, AlertCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Helper to get cookie value
const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
};

export default function JobDetail() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(true);

  useEffect(() => {
    loadJobDetails();
  }, [jobId]);

  useEffect(() => {
    if (!polling) return;

    const interval = setInterval(() => {
      loadJobDetails(true);
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(interval);
  }, [polling]);

  const loadJobDetails = async (isPolling = false) => {
    try {
      const jobRes = await axios.get(`${BACKEND_URL}/api/jobs/${jobId}`, {
        withCredentials: true
      });
      const jobData = jobRes.data;
      setJob(jobData);

      // Stop polling if job is completed or failed
      if (jobData.status === 'completed' || jobData.status === 'failed') {
        setPolling(false);
      }

      // Load agent details
      const agentRes = await axios.get(`${BACKEND_URL}/api/agents/${jobData.agent_id}`, {
        withCredentials: true
      });
      setAgent(agentRes.data);
    } catch (error) {
      console.error('Failed to load job:', error);
      if (error.response?.status === 401) {
        navigate('/');
      }
    } finally {
      if (!isPolling) {
        setLoading(false);
      }
    }
  };

  // Generate download URL for a file
  const getDownloadUrl = (filename) => {
    const token = getCookie('session_token');
    return `${BACKEND_URL}/api/jobs/${jobId}/download/${encodeURIComponent(filename)}${token ? `?token=${encodeURIComponent(token)}` : ''}`;
  };

  // Handle file download using fetch + blob
  const handleDownload = async (filename) => {
    try {
      const url = getDownloadUrl(filename);
      const response = await fetch(url, {
        method: 'GET',
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error('Download failed');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Download error:', error);
      // Fallback: open in new tab
      window.open(getDownloadUrl(filename), '_blank');
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-amber-50 text-amber-700 border-amber-200',
      processing: 'bg-sky-50 text-sky-700 border-sky-200',
      completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      failed: 'bg-red-50 text-red-700 border-red-200'
    };
    return styles[status] || styles.pending;
  };

  const getStatusIcon = (status) => {
    if (status === 'completed') return <CheckCircle2 className="w-5 h-5" />;
    if (status === 'processing') return <Zap className="w-5 h-5 animate-pulse" />;
    if (status === 'failed') return <XCircle className="w-5 h-5" />;
    return <Clock className="w-5 h-5" />;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Job not found</h2>
          <Link to="/dashboard" className="text-blue-600 hover:text-blue-700">
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <Link
            to="/jobs"
            className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Jobs
          </Link>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-slate-900 mb-2" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Job Details
              </h1>
              <p className="text-slate-600 font-mono text-sm">
                Job ID: {job.job_id}
              </p>
            </div>
            <span className={`inline-flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-md border ${getStatusBadge(job.status)}`}>
              {getStatusIcon(job.status)}
              {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Job Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Agent Info */}
            <div className="bg-white rounded-lg border border-slate-200 p-6 fade-in">
              <h3 className="text-lg font-semibold text-slate-900 mb-4" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Agent Information
              </h3>
              <div className="space-y-3">
                <div>
                  <div className="text-sm text-slate-500 mb-1">Agent Name</div>
                  <div className="text-base text-slate-900 font-medium">{agent?.name}</div>
                </div>
                <div>
                  <div className="text-sm text-slate-500 mb-1">Description</div>
                  <div className="text-base text-slate-700">{agent?.description}</div>
                </div>
              </div>
            </div>

            {/* Input Files */}
            <div className="bg-white rounded-lg border border-slate-200 p-6 fade-in">
              <h3 className="text-lg font-semibold text-slate-900 mb-4" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Input Files
              </h3>
              <div className="space-y-2">
                {job.input_files.map((file, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-3 bg-slate-50 rounded-md">
                    <FileText className="w-5 h-5 text-slate-600" />
                    <span className="text-sm text-slate-900">{file}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Output Files */}
            {job.status === 'completed' && job.output_files.length > 0 && (
              <div className="bg-white rounded-lg border border-slate-200 p-6 fade-in" data-testid="output-files-section">
                <h3 className="text-lg font-semibold text-slate-900 mb-4" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                  Output Files
                </h3>
                <div className="space-y-2">
                  {job.output_files.map((file, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-emerald-50 rounded-md border border-emerald-200">
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-emerald-600" />
                        <span className="text-sm text-slate-900 font-medium">{file}</span>
                      </div>
                      <a
                        href={getDownloadUrl(file)}
                        download={file}
                        data-testid="download-btn"
                        className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-600 text-white text-sm rounded-md hover:bg-emerald-700 transition-all cursor-pointer"
                      >
                        <Download className="w-4 h-4" />
                        Download
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Script Outputs */}
            {(job.validation_output || job.execution_output) && (
              <div className="bg-slate-900 rounded-lg p-6 fade-in">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  Script Output
                </h3>
                
                {job.validation_output && (
                  <div className="mb-4">
                    <div className="text-sm text-emerald-400 font-medium mb-2">Validation Script:</div>
                    <pre className="text-xs text-slate-300 font-mono bg-slate-800 p-4 rounded-md overflow-x-auto whitespace-pre-wrap">
                      {job.validation_output}
                    </pre>
                  </div>
                )}
                
                {job.execution_output && (
                  <div>
                    <div className="text-sm text-blue-400 font-medium mb-2">Main Script:</div>
                    <pre className="text-xs text-slate-300 font-mono bg-slate-800 p-4 rounded-md overflow-x-auto whitespace-pre-wrap">
                      {job.execution_output}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Error Message */}
            {job.status === 'failed' && job.error_message && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-6 fade-in">
                <div className="flex items-start gap-3">
                  <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium text-red-900 mb-1">Job Failed</div>
                    <div className="text-sm text-red-700">
                      {job.error_message}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Processing Status */}
            {job.status === 'processing' && (
              <div className="bg-sky-50 border border-sky-200 rounded-lg p-6 fade-in">
                <div className="flex items-start gap-3">
                  <div className="loading-spinner w-5 h-5 flex-shrink-0 mt-0.5" style={{ width: '20px', height: '20px', borderWidth: '2px' }}></div>
                  <div>
                    <div className="font-medium text-sky-900 mb-1">Processing...</div>
                    <div className="text-sm text-sky-700">
                      Your job is being processed. This page will update automatically.
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Pending Status */}
            {job.status === 'pending' && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 fade-in">
                <div className="flex items-start gap-3">
                  <Clock className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium text-amber-900 mb-1">Pending Execution</div>
                    <div className="text-sm text-amber-700">
                      Job is waiting to be executed. Go back to the agent page to trigger execution.
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Column - Timeline */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-slate-200 p-6 fade-in">
              <h3 className="text-lg font-semibold text-slate-900 mb-4" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Timeline
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="text-sm text-slate-500 mb-1">Created</div>
                  <div className="text-sm text-slate-900">
                    {new Date(job.created_at).toLocaleDateString()} at {new Date(job.created_at).toLocaleTimeString()}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-slate-500 mb-1">Last Updated</div>
                  <div className="text-sm text-slate-900">
                    {new Date(job.updated_at).toLocaleDateString()} at {new Date(job.updated_at).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white rounded-lg border border-slate-200 p-6 fade-in">
              <h3 className="text-lg font-semibold text-slate-900 mb-4" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Quick Actions
              </h3>
              <div className="space-y-2">
                <Link
                  to={`/agent/${job.agent_id}`}
                  className="block w-full py-2 px-4 bg-slate-900 text-white text-center rounded-md hover:bg-slate-800 transition-all text-sm font-medium"
                >
                  Run Agent Again
                </Link>
                <Link
                  to="/jobs"
                  className="block w-full py-2 px-4 bg-white border border-slate-200 text-slate-900 text-center rounded-md hover:bg-slate-50 transition-all text-sm font-medium"
                >
                  View All Jobs
                </Link>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
