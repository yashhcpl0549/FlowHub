import { useEffect, useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import axios from 'axios';
import { Play, Zap, Clock, CheckCircle2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function Dashboard() {
  const [agents, setAgents] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // If user data passed from AuthCallback, use it directly
    if (location.state?.user) {
      setUser(location.state.user);
      loadData();
    } else {
      // Otherwise verify session
      checkAuth();
    }
  }, []);

  const checkAuth = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/auth/me`, {
        withCredentials: true
      });
      setUser(response.data);
      loadData();
    } catch (error) {
      console.error('Auth check failed:', error);
      navigate('/');
    }
  };

  const loadData = async () => {
    try {
      const [agentsRes, jobsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/agents`, { withCredentials: true }),
        axios.get(`${BACKEND_URL}/api/jobs`, { withCredentials: true })
      ]);
      setAgents(agentsRes.data);
      setJobs(jobsRes.data.slice(0, 5)); // Latest 5 jobs
    } catch (error) {
      console.error('Failed to load data:', error);
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
      <header className="bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-slate-900 rounded-lg flex items-center justify-center">
                <Play className="w-5 h-5 text-white" strokeWidth={2} />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                  Honasa Task Force
                </h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
              {user?.role === 'admin' && (
                <Link
                  to="/admin"
                  data-testid="admin-link"
                  className="text-sm bg-amber-50 text-amber-700 px-3 py-1.5 rounded-md border border-amber-200 hover:bg-amber-100 transition-all font-medium"
                >
                  Admin Panel
                </Link>
              )}
              {/* Admin link */}
              <div className="text-right">
                <div className="text-sm font-medium text-slate-900">{user?.name}</div>
                <div className="text-xs text-slate-500">{user?.email}</div>
              </div>
              <img
                src={user?.picture || 'https://via.placeholder.com/40'}
                alt={user?.name}
                className="w-10 h-10 rounded-full border-2 border-slate-200"
              />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        {/* Welcome Section */}
        <div className="mb-10 fade-in">
          <h2 className="text-4xl font-semibold text-slate-900 mb-3" style={{ fontFamily: 'Work Sans, sans-serif' }}>
            Welcome back, {user?.name?.split(' ')[0]}
          </h2>
          <p className="text-lg text-slate-600">
            Select an automation agent to process your data or check recent job status below.
          </p>
        </div>

        {/* Agents Grid */}
        <div className="mb-10">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-medium text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
              Available Agents
            </h3>
            <span className="text-sm text-slate-500">{agents.length} agents</span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agents.map((agent, index) => {
              return (
                <Link
                  key={agent.agent_id}
                  to={`/agent/${agent.agent_id}`}
                  data-testid={`agent-card-${index}`}
                  className="agent-card bg-white rounded-lg border border-slate-200 p-6 hover:shadow-lg block"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-12 h-12 rounded-lg flex items-center justify-center bg-blue-50">
                      <Zap className="w-6 h-6 text-blue-600" strokeWidth={1.5} />
                    </div>
                    <div className="flex items-center gap-2">
                      {agent.tag && (
                        <span className={`text-xs font-medium px-2 py-1 rounded-md border ${
                          agent.tag === 'Finance' 
                            ? 'text-purple-600 bg-purple-50 border-purple-200'
                            : agent.tag === 'Marketing'
                            ? 'text-orange-600 bg-orange-50 border-orange-200'
                            : agent.tag === 'HR'
                            ? 'text-blue-600 bg-blue-50 border-blue-200'
                            : agent.tag === 'Customer Support'
                            ? 'text-teal-600 bg-teal-50 border-teal-200'
                            : agent.tag === 'Revenue'
                            ? 'text-green-600 bg-green-50 border-green-200'
                            : agent.tag === 'Analytics'
                            ? 'text-cyan-600 bg-cyan-50 border-cyan-200'
                            : 'text-slate-600 bg-slate-50 border-slate-200'
                        }`}>
                          {agent.tag}
                        </span>
                      )}
                      <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md border border-emerald-200">
                        Active
                      </span>
                    </div>
                  </div>
                  <h4 className="text-lg font-semibold text-slate-900 mb-2" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                    {agent.name}
                  </h4>
                  <p className="text-sm text-slate-600 leading-relaxed mb-4">
                    {agent.description}
                  </p>
                  <div className="pt-4 border-t border-slate-100">
                    <div className="text-xs text-slate-500 mb-2">Required Files:</div>
                    <div className="flex flex-wrap gap-2">
                      {agent.required_files.map((file, idx) => (
                        <span key={idx} className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
                          {file}
                        </span>
                      ))}
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Recent Jobs */}
        {jobs.length > 0 && (
          <div className="fade-in">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-2xl font-medium text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Recent Jobs
              </h3>
              <Link to="/jobs" className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                View all →
              </Link>
            </div>
            
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="text-left p-4 text-sm font-medium text-slate-900">Job ID</th>
                      <th className="text-left p-4 text-sm font-medium text-slate-900">Agent</th>
                      <th className="text-left p-4 text-sm font-medium text-slate-900">Status</th>
                      <th className="text-left p-4 text-sm font-medium text-slate-900">Created</th>
                      <th className="text-left p-4 text-sm font-medium text-slate-900">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.map((job) => (
                      <tr key={job.job_id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors" data-testid="job-row">
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
                            {new Date(job.created_at).toLocaleDateString()}
                          </span>
                        </td>
                        <td className="p-4">
                          <Link
                            to={`/jobs/${job.job_id}`}
                            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                          >
                            View →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
