import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Clock, CheckCircle2, XCircle, Zap } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function JobsList() {
  const [jobs, setJobs] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [jobsRes, agentsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/jobs`, { withCredentials: true }),
        axios.get(`${BACKEND_URL}/api/agents`, { withCredentials: true })
      ]);
      setJobs(jobsRes.data);
      setAgents(agentsRes.data);
    } catch (error) {
      console.error('Failed to load jobs:', error);
      if (error.response?.status === 401) {
        navigate('/');
      }
    } finally {
      setLoading(false);
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
    if (status === 'completed') return <CheckCircle2 className="w-4 h-4" />;
    if (status === 'processing') return <Zap className="w-4 h-4 animate-pulse" />;
    if (status === 'failed') return <XCircle className="w-4 h-4" />;
    return <Clock className="w-4 h-4" />;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
          <h1 className="text-3xl font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
            Job History
          </h1>
          <p className="text-slate-600 mt-2">
            View all your automation jobs and their status
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        {jobs.length === 0 ? (
          <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
            <Clock className="w-12 h-12 text-slate-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 mb-2">No jobs yet</h3>
            <p className="text-slate-600 mb-6">Start by selecting an agent from the dashboard</p>
            <Link
              to="/dashboard"
              className="inline-block py-2 px-4 bg-slate-900 text-white rounded-md hover:bg-slate-800 transition-all"
            >
              Go to Dashboard
            </Link>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-slate-200 overflow-hidden fade-in">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="text-left p-4 text-sm font-medium text-slate-900">Job ID</th>
                    <th className="text-left p-4 text-sm font-medium text-slate-900">Agent</th>
                    <th className="text-left p-4 text-sm font-medium text-slate-900">Status</th>
                    <th className="text-left p-4 text-sm font-medium text-slate-900">Input Files</th>
                    <th className="text-left p-4 text-sm font-medium text-slate-900">Created</th>
                    <th className="text-left p-4 text-sm font-medium text-slate-900">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => (
                    <tr key={job.job_id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                      <td className="p-4">
                        <span className="text-sm font-mono text-slate-700">{job.job_id}</span>
                      </td>
                      <td className="p-4">
                        <span className="text-sm text-slate-900">
                          {agents.find(a => a.agent_id === job.agent_id)?.name || job.agent_id}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-md border ${getStatusBadge(job.status)}`}>
                          {getStatusIcon(job.status)}
                          {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className="text-sm text-slate-600">
                          {job.input_files.length} file{job.input_files.length !== 1 ? 's' : ''}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className="text-sm text-slate-600">
                          {new Date(job.created_at).toLocaleDateString()} {new Date(job.created_at).toLocaleTimeString()}
                        </span>
                      </td>
                      <td className="p-4">
                        <Link
                          to={`/jobs/${job.job_id}`}
                          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                        >
                          View Details →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
