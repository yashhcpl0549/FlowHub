import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Plus, Trash2, FileText, Upload } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function ManageAgents() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    required_files: '',
    validation_file: null,
    main_file: null
  });

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/admin/agents`, {
        withCredentials: true
      });
      setAgents(response.data);
    } catch (error) {
      console.error('Failed to load agents:', error);
      if (error.response?.status === 403 || error.response?.status === 401) {
        navigate('/');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e, field) => {
    setFormData({
      ...formData,
      [field]: e.target.files[0]
    });
  };

  const handleCreateAgent = async (e) => {
    e.preventDefault();
    setCreating(true);

    const data = new FormData();
    data.append('name', formData.name);
    data.append('description', formData.description);
    data.append('required_files', formData.required_files);
    
    if (formData.validation_file) {
      data.append('validation_file', formData.validation_file);
    }
    if (formData.main_file) {
      data.append('main_file', formData.main_file);
    }

    try {
      await axios.post(
        `${BACKEND_URL}/api/admin/agents`,
        data,
        {
          withCredentials: true,
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );

      toast.success('Agent created successfully!');
      setShowCreateModal(false);
      setFormData({
        name: '',
        description: '',
        required_files: '',
        validation_file: null,
        main_file: null
      });
      loadAgents();
    } catch (error) {
      console.error('Failed to create agent:', error);
      toast.error(error.response?.data?.detail || 'Failed to create agent');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteAgent = async (agentId, agentName) => {
    if (!window.confirm(`Are you sure you want to delete "${agentName}"?`)) {
      return;
    }

    try {
      await axios.delete(
        `${BACKEND_URL}/api/admin/agents/${agentId}`,
        { withCredentials: true }
      );
      toast.success('Agent deleted successfully');
      loadAgents();
    } catch (error) {
      console.error('Failed to delete agent:', error);
      toast.error('Failed to delete agent');
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
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Manage Agents
              </h1>
              <p className="text-slate-600 mt-2">
                Create and configure automation agents
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              data-testid="create-agent-btn"
              className="inline-flex items-center gap-2 py-2 px-4 bg-slate-900 text-white rounded-md hover:bg-slate-800 transition-all font-medium shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Create Agent
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <div
              key={agent.agent_id}
              className="bg-white rounded-lg border border-slate-200 p-6 fade-in"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                      {agent.name}
                    </h3>
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
                          : 'text-slate-600 bg-slate-50 border-slate-200'
                      }`}>
                        {agent.tag}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed mb-3">
                    {agent.description}
                  </p>
                </div>
              </div>

              <div className="mb-4 pt-4 border-t border-slate-100">
                <div className="text-xs text-slate-500 mb-2">Required Files:</div>
                <div className="flex flex-wrap gap-2">
                  {agent.required_files.map((file, idx) => (
                    <span key={idx} className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
                      {file}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-500 mb-4">
                {agent.validation_script && (
                  <span className="flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    Validation
                  </span>
                )}
                {agent.main_script && (
                  <span className="flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    Main Script
                  </span>
                )}
              </div>

              <button
                onClick={() => handleDeleteAgent(agent.agent_id, agent.name)}
                className="w-full py-2 px-4 border border-red-200 text-red-600 rounded-md hover:bg-red-50 transition-all text-sm font-medium flex items-center justify-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Delete Agent
              </button>
            </div>
          ))}
        </div>
      </main>

      {/* Create Agent Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-2xl fade-in">
            <div className="p-6 border-b border-slate-200">
              <h3 className="text-xl font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Create New Agent
              </h3>
              <p className="text-sm text-slate-600 mt-1">
                Define agent details and upload processing scripts
              </p>
            </div>

            <form onSubmit={handleCreateAgent} className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="space-y-4">
                {/* Agent Name */}
                <div>
                  <label className="block text-sm font-medium text-slate-900 mb-2">
                    Agent Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., Monthly Sales Report Generator"
                    className="w-full px-3 py-2 border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm font-medium text-slate-900 mb-2">
                    Description *
                  </label>
                  <textarea
                    required
                    rows={3}
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Describe what this agent does..."
                    className="w-full px-3 py-2 border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Required Files */}
                <div>
                  <label className="block text-sm font-medium text-slate-900 mb-2">
                    Required Files (comma-separated) *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.required_files}
                    onChange={(e) => setFormData({ ...formData, required_files: e.target.value })}
                    placeholder="e.g., Sales Data, Customer List, Config File"
                    className="w-full px-3 py-2 border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    List the input files required for this agent
                  </p>
                </div>

                {/* Validation Script */}
                <div>
                  <label className="block text-sm font-medium text-slate-900 mb-2">
                    Validation Script (Python .py file)
                  </label>
                  <div className="border-2 border-dashed border-slate-300 rounded-lg p-4 hover:border-blue-400 transition-colors">
                    <input
                      type="file"
                      accept=".py"
                      onChange={(e) => handleFileChange(e, 'validation_file')}
                      className="hidden"
                      id="validation-file"
                    />
                    <label
                      htmlFor="validation-file"
                      className="cursor-pointer flex items-center gap-3"
                    >
                      <Upload className="w-5 h-5 text-slate-400" />
                      <div>
                        <div className="text-sm text-slate-700">
                          {formData.validation_file ? formData.validation_file.name : 'Click to upload validation script'}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          Optional: Script to validate input files before processing
                        </div>
                      </div>
                    </label>
                  </div>
                </div>

                {/* Main Script */}
                <div>
                  <label className="block text-sm font-medium text-slate-900 mb-2">
                    Main Processing Script (Python .py file)
                  </label>
                  <div className="border-2 border-dashed border-slate-300 rounded-lg p-4 hover:border-blue-400 transition-colors">
                    <input
                      type="file"
                      accept=".py"
                      onChange={(e) => handleFileChange(e, 'main_file')}
                      className="hidden"
                      id="main-file"
                    />
                    <label
                      htmlFor="main-file"
                      className="cursor-pointer flex items-center gap-3"
                    >
                      <Upload className="w-5 h-5 text-slate-400" />
                      <div>
                        <div className="text-sm text-slate-700">
                          {formData.main_file ? formData.main_file.name : 'Click to upload main script'}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          Optional: Main processing script for this agent
                        </div>
                      </div>
                    </label>
                  </div>
                </div>
              </div>
            </form>

            <div className="p-6 border-t border-slate-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                type="button"
                className="py-2 px-4 border border-slate-200 text-slate-700 rounded-md hover:bg-slate-50 transition-all font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateAgent}
                disabled={creating}
                data-testid="submit-agent-btn"
                className="py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-slate-300 transition-all font-medium shadow-sm"
              >
                {creating ? 'Creating...' : 'Create Agent'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
