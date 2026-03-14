import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Edit2, FileText, Users, ChevronRight, X, Upload, RefreshCw } from 'lucide-react';

const BACKEND = process.env.REACT_APP_BACKEND_URL || '';

export default function ManageAgents() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editAgent, setEditAgent] = useState(null); // agent object being edited
  const [creating, setCreating] = useState(false);
  const [formData, setFormData] = useState({
    name: '', description: '', required_files: '',
    validation_file: null, main_file: null
  });

  useEffect(() => { fetchAgents(); }, []);

  async function fetchAgents() {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND}/api/admin/agents`, { credentials: 'include' });
      if (res.ok) setAgents(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  }

  function openCreate() {
    setFormData({ name: '', description: '', required_files: '', validation_file: null, main_file: null });
    setEditAgent(null);
    setShowCreateModal(true);
  }

  function openEdit(agent) {
    setFormData({
      name: agent.name,
      description: agent.description,
      required_files: Array.isArray(agent.required_files) ? agent.required_files.join(', ') : (agent.required_files || ''),
      validation_file: null,
      main_file: null
    });
    setEditAgent(agent);
    setShowCreateModal(true);
  }

  function closeModal() {
    setShowCreateModal(false);
    setEditAgent(null);
    setFormData({ name: '', description: '', required_files: '', validation_file: null, main_file: null });
  }

  function handleFileChange(e, field) {
    const file = e.target.files[0];
    if (file) setFormData(prev => ({ ...prev, [field]: file }));
  }

  async function handleSubmit() {
    if (!formData.name.trim() || !formData.description.trim()) {
      alert('Name and description are required');
      return;
    }
    setCreating(true);
    try {
      const fd = new FormData();
      fd.append('name', formData.name);
      fd.append('description', formData.description);
      fd.append('required_files', formData.required_files);
      if (formData.validation_file) fd.append('validation_file', formData.validation_file);
      if (formData.main_file) fd.append('main_file', formData.main_file);

      const url = editAgent
        ? `${BACKEND}/api/admin/agents/${editAgent.agent_id}`
        : `${BACKEND}/api/admin/agents`;
      const method = editAgent ? 'PUT' : 'POST';

      const res = await fetch(url, { method, credentials: 'include', body: fd });
      if (res.ok) {
        closeModal();
        fetchAgents();
      } else {
        const err = await res.json();
        alert(err.detail || 'Failed to save agent');
      }
    } catch (e) {
      alert('Error saving agent');
    }
    setCreating(false);
  }

  async function handleDelete(agentId, name) {
    if (!window.confirm(`Delete agent "${name}"? This cannot be undone.`)) return;
    try {
      const res = await fetch(`${BACKEND}/api/admin/agents/${agentId}`, {
        method: 'DELETE', credentials: 'include'
      });
      if (res.ok) fetchAgents();
      else alert('Failed to delete agent');
    } catch (e) { alert('Error deleting agent'); }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
              Manage Agents
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">{agents.length} agent{agents.length !== 1 ? 's' : ''} configured</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={fetchAgents} className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={openCreate}
              className="flex items-center gap-2 py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-all font-medium shadow-sm text-sm"
            >
              <Plus className="w-4 h-4" /> New Agent
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : agents.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Plus className="w-8 h-8 text-slate-400" />
            </div>
            <p className="text-slate-600 font-medium">No agents yet</p>
            <p className="text-slate-400 text-sm mt-1">Create your first agent to get started</p>
            <button onClick={openCreate} className="mt-4 py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium">
              Create Agent
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map(agent => (
              <div key={agent.agent_id} className="bg-white rounded-lg border border-slate-200 p-5 hover:shadow-sm transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-slate-900 truncate">{agent.name}</h3>
                    <p className="text-xs text-slate-400 mt-0.5 font-mono truncate">{agent.agent_id}</p>
                  </div>
                  <span className={`ml-2 flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${
                    agent.status === 'active' ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-slate-500'
                  }`}>
                    {agent.status}
                  </span>
                </div>

                <p className="text-sm text-slate-600 mb-4 line-clamp-2">{agent.description}</p>

                {agent.required_files?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-medium text-slate-500 mb-1.5">Required files</p>
                    <div className="flex flex-wrap gap-1.5">
                      {agent.required_files.slice(0, 3).map((f, i) => (
                        <span key={i} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">{f}</span>
                      ))}
                      {agent.required_files.length > 3 && (
                        <span className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded text-xs">+{agent.required_files.length - 3} more</span>
                      )}
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-4">
                  {agent.validation_script && (
                    <span className="flex items-center gap-1 bg-slate-50 px-2 py-0.5 rounded">
                      <FileText className="w-3 h-3" /> Validation
                    </span>
                  )}
                  {agent.main_script && (
                    <span className="flex items-center gap-1 bg-slate-50 px-2 py-0.5 rounded">
                      <FileText className="w-3 h-3" /> Main Script
                    </span>
                  )}
                </div>

                <div className="flex gap-2 pt-3 border-t border-slate-100">
                  <button
                    onClick={() => openEdit(agent)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 border border-slate-200 text-slate-700 rounded-md hover:bg-slate-50 transition-all text-sm font-medium"
                  >
                    <Edit2 className="w-3.5 h-3.5" /> Edit
                  </button>
                  <button
                    onClick={() => handleDelete(agent.agent_id, agent.name)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 border border-red-200 text-red-600 rounded-md hover:bg-red-50 transition-all text-sm font-medium"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create / Edit Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-2xl">
            <div className="p-6 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                  {editAgent ? 'Edit Agent' : 'Create New Agent'}
                </h3>
                <p className="text-sm text-slate-500 mt-0.5">
                  {editAgent ? 'Update agent details and scripts' : 'Define agent details and upload processing scripts'}
                </p>
              </div>
              <button onClick={closeModal} className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-md transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)] space-y-5">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-slate-900 mb-1.5">Agent Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e => setFormData(p => ({ ...p, name: e.target.value }))}
                  placeholder="e.g. KE30 Sale Register"
                  className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-slate-900 mb-1.5">Description *</label>
                <textarea
                  value={formData.description}
                  onChange={e => setFormData(p => ({ ...p, description: e.target.value }))}
                  placeholder="What does this agent do?"
                  rows={3}
                  className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
              </div>

              {/* Required files */}
              <div>
                <label className="block text-sm font-medium text-slate-900 mb-1.5">Required Files</label>
                <input
                  type="text"
                  value={formData.required_files}
                  onChange={e => setFormData(p => ({ ...p, required_files: e.target.value }))}
                  placeholder="e.g. KE30 Export, Customer Mapping, MRP File"
                  className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p className="text-xs text-slate-400 mt-1">Comma-separated list shown to users when uploading</p>
              </div>

              {/* Scripts */}
              <div className="grid grid-cols-2 gap-4">
                {/* Validation script */}
                <div>
                  <label className="block text-sm font-medium text-slate-900 mb-1.5">
                    Validation Script (.py)
                    {editAgent?.validation_script && <span className="ml-2 text-xs text-green-600 font-normal">✓ uploaded</span>}
                  </label>
                  <label className="cursor-pointer block border-2 border-dashed border-slate-200 rounded-lg p-4 hover:border-blue-400 transition-colors text-center">
                    <input type="file" accept=".py" onChange={e => handleFileChange(e, 'validation_file')} className="hidden" />
                    <Upload className="w-5 h-5 text-slate-400 mx-auto mb-1" />
                    <div className="text-xs text-slate-600">
                      {formData.validation_file ? formData.validation_file.name : (editAgent ? 'Replace validate.py' : 'Upload validate.py')}
                    </div>
                  </label>
                </div>

                {/* Main script */}
                <div>
                  <label className="block text-sm font-medium text-slate-900 mb-1.5">
                    Main Script (.py)
                    {editAgent?.main_script && <span className="ml-2 text-xs text-green-600 font-normal">✓ uploaded</span>}
                  </label>
                  <label className="cursor-pointer block border-2 border-dashed border-slate-200 rounded-lg p-4 hover:border-blue-400 transition-colors text-center">
                    <input type="file" accept=".py" onChange={e => handleFileChange(e, 'main_file')} className="hidden" />
                    <Upload className="w-5 h-5 text-slate-400 mx-auto mb-1" />
                    <div className="text-xs text-slate-600">
                      {formData.main_file ? formData.main_file.name : (editAgent ? 'Replace main.py' : 'Upload main.py')}
                    </div>
                  </label>
                </div>
              </div>
              {editAgent && (
                <p className="text-xs text-slate-400">Leave script fields empty to keep existing scripts unchanged.</p>
              )}
            </div>

            <div className="p-4 border-t border-slate-200 flex items-center justify-end gap-3">
              <button onClick={closeModal} className="py-2 px-4 border border-slate-200 text-slate-700 rounded-md hover:bg-slate-50 text-sm font-medium">
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={creating}
                className="py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-slate-300 text-sm font-medium shadow-sm"
              >
                {creating ? 'Saving...' : (editAgent ? 'Save Changes' : 'Create Agent')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
