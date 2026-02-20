import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Users, CheckCircle2, Shield } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function ManageUsers() {
  const [users, setUsers] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedAccess, setSelectedAccess] = useState([]);
  const [updatingRole, setUpdatingRole] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [usersRes, agentsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/admin/users`, { withCredentials: true }),
        axios.get(`${BACKEND_URL}/api/admin/agents`, { withCredentials: true })
      ]);
      setUsers(usersRes.data);
      setAgents(agentsRes.data);
    } catch (error) {
      console.error('Failed to load data:', error);
      if (error.response?.status === 403 || error.response?.status === 401) {
        navigate('/');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleEditAccess = (user) => {
    setSelectedUser(user);
    setSelectedAccess(user.agent_access || []);
  };

  const toggleAgentAccess = (agentId) => {
    if (selectedAccess.includes(agentId)) {
      setSelectedAccess(selectedAccess.filter(id => id !== agentId));
    } else {
      setSelectedAccess([...selectedAccess, agentId]);
    }
  };

  const saveAccess = async () => {
    try {
      await axios.put(
        `${BACKEND_URL}/api/admin/users/${selectedUser.user_id}/access`,
        selectedAccess,
        { 
          withCredentials: true,
          headers: { 'Content-Type': 'application/json' }
        }
      );
      
      toast.success('User access updated successfully');
      setSelectedUser(null);
      loadData();
    } catch (error) {
      console.error('Failed to update access:', error);
      toast.error('Failed to update user access');
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
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <Link
            to="/admin"
            className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Admin
          </Link>
          <h1 className="text-3xl font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
            Manage Users
          </h1>
          <p className="text-slate-600 mt-2">
            Control user access to automation agents
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden fade-in">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left p-4 text-sm font-medium text-slate-900">User</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-900">Email</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-900">Role</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-900">Agent Access</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-900">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.user_id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <img
                          src={user.picture || 'https://via.placeholder.com/40'}
                          alt={user.name}
                          className="w-8 h-8 rounded-full border border-slate-200"
                        />
                        <span className="text-sm font-medium text-slate-900">{user.name}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="text-sm text-slate-600">{user.email}</span>
                    </td>
                    <td className="p-4">
                      {user.role === 'admin' ? (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-md bg-amber-50 text-amber-700 border border-amber-200">
                          <Shield className="w-3 h-3" />
                          Admin
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                          <Users className="w-3 h-3" />
                          User
                        </span>
                      )}
                    </td>
                    <td className="p-4">
                      <span className="text-sm text-slate-600">
                        {user.agent_access?.length || 0} agent{user.agent_access?.length !== 1 ? 's' : ''}
                      </span>
                    </td>
                    <td className="p-4">
                      {user.role !== 'admin' && (
                        <button
                          onClick={() => handleEditAccess(user)}
                          data-testid="edit-access-btn"
                          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                        >
                          Edit Access
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Access Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-2xl fade-in">
            <div className="p-6 border-b border-slate-200">
              <h3 className="text-xl font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Edit Agent Access
              </h3>
              <p className="text-sm text-slate-600 mt-1">
                {selectedUser.name} ({selectedUser.email})
              </p>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[50vh]">
              <div className="space-y-3">
                {agents.map((agent) => (
                  <label
                    key={agent.agent_id}
                    className="flex items-start gap-3 p-4 border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedAccess.includes(agent.agent_id)}
                      onChange={() => toggleAgentAccess(agent.agent_id)}
                      className="mt-1 w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-slate-900">{agent.name}</div>
                      <div className="text-sm text-slate-600 mt-1">{agent.description}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
            
            <div className="p-6 border-t border-slate-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setSelectedUser(null)}
                className="py-2 px-4 border border-slate-200 text-slate-700 rounded-md hover:bg-slate-50 transition-all font-medium"
              >
                Cancel
              </button>
              <button
                onClick={saveAccess}
                data-testid="save-access-btn"
                className="py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-all font-medium shadow-sm"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
