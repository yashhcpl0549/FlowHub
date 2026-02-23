import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { Play, Users, Zap, Plus, Shield, Settings } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function AdminDashboard() {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState({ users: 0, agents: 0, jobs: 0 });
  const navigate = useNavigate();

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/auth/me`, {
        withCredentials: true
      });
      
      if (response.data.role !== 'admin') {
        navigate('/dashboard');
        return;
      }
      
      setUser(response.data);
      loadStats();
    } catch (error) {
      console.error('Auth check failed:', error);
      navigate('/');
    }
  };

  const loadStats = async () => {
    try {
      const [usersRes, agentsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/admin/users`, { withCredentials: true }),
        axios.get(`${BACKEND_URL}/api/admin/agents`, { withCredentials: true })
      ]);
      
      setStats({
        users: usersRes.data.length,
        agents: agentsRes.data.length,
        jobs: 0
      });
    } catch (error) {
      console.error('Failed to load stats:', error);
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
                  Honasa Task Force Admin
                </h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <Link
                to="/dashboard"
                className="text-sm text-slate-600 hover:text-slate-900"
              >
                User View
              </Link>
              <div className="text-right">
                <div className="text-sm font-medium text-slate-900">{user?.name}</div>
                <div className="text-xs text-amber-600 font-medium">Admin</div>
              </div>
              <img
                src={user?.picture || 'https://via.placeholder.com/40'}
                alt={user?.name}
                className="w-10 h-10 rounded-full border-2 border-amber-200"
              />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        {/* Welcome Section */}
        <div className="mb-10 fade-in">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-8 h-8 text-amber-600" />
            <h2 className="text-4xl font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
              Admin Dashboard
            </h2>
          </div>
          <p className="text-lg text-slate-600">
            Manage users, agents, and system settings
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
              <span className="text-3xl font-semibold text-slate-900">{stats.users}</span>
            </div>
            <h3 className="text-sm font-medium text-slate-600">Total Users</h3>
          </div>
          
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-emerald-50 rounded-lg flex items-center justify-center">
                <Zap className="w-6 h-6 text-emerald-600" />
              </div>
              <span className="text-3xl font-semibold text-slate-900">{stats.agents}</span>
            </div>
            <h3 className="text-sm font-medium text-slate-600">Active Agents</h3>
          </div>
          
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-purple-50 rounded-lg flex items-center justify-center">
                <Settings className="w-6 h-6 text-purple-600" />
              </div>
              <span className="text-sm font-medium text-slate-600 mt-2">System Status</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-slate-900 font-medium">All Systems Operational</span>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link
            to="/admin/users"
            data-testid="manage-users-link"
            className="bg-white rounded-lg border border-slate-200 p-8 hover:shadow-lg transition-all hover:-translate-y-1 block"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="w-14 h-14 bg-blue-50 rounded-lg flex items-center justify-center">
                <Users className="w-7 h-7 text-blue-600" strokeWidth={1.5} />
              </div>
              <span className="text-blue-600 text-sm font-medium">→</span>
            </div>
            <h3 className="text-2xl font-semibold text-slate-900 mb-2" style={{ fontFamily: 'Work Sans, sans-serif' }}>
              Manage Users
            </h3>
            <p className="text-slate-600">
              Control user access to agents and manage permissions
            </p>
          </Link>

          <Link
            to="/admin/agents"
            data-testid="manage-agents-link"
            className="bg-white rounded-lg border border-slate-200 p-8 hover:shadow-lg transition-all hover:-translate-y-1 block"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="w-14 h-14 bg-emerald-50 rounded-lg flex items-center justify-center">
                <Zap className="w-7 h-7 text-emerald-600" strokeWidth={1.5} />
              </div>
              <span className="text-emerald-600 text-sm font-medium">→</span>
            </div>
            <h3 className="text-2xl font-semibold text-slate-900 mb-2" style={{ fontFamily: 'Work Sans, sans-serif' }}>
              Manage Agents
            </h3>
            <p className="text-slate-600">
              Create, edit, and configure automation agents
            </p>
          </Link>
        </div>
      </main>
    </div>
  );
}
