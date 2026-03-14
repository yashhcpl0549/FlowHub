import React, { useState, useEffect } from 'react';
import { Users, Shield, ShieldOff, Search, RefreshCw, CheckSquare, Square, ChevronDown, ChevronUp } from 'lucide-react';

const BACKEND = process.env.REACT_APP_BACKEND_URL || '';

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expandedUser, setExpandedUser] = useState(null);
  const [saving, setSaving] = useState({});

  useEffect(() => {
    fetchAll();
  }, []);

  async function fetchAll() {
    setLoading(true);
    try {
      const [uRes, aRes] = await Promise.all([
        fetch(`${BACKEND}/api/admin/users`, { credentials: 'include' }),
        fetch(`${BACKEND}/api/admin/agents`, { credentials: 'include' })
      ]);
      if (uRes.ok) setUsers(await uRes.json());
      if (aRes.ok) setAgents(await aRes.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  }

  async function updateRole(userId, newRole) {
    setSaving(s => ({ ...s, [userId + '_role']: true }));
    try {
      const res = await fetch(`${BACKEND}/api/admin/users/${userId}/role`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole })
      });
      if (res.ok) fetchAll();
      else alert('Failed to update role');
    } catch (e) { alert('Error updating role'); }
    setSaving(s => ({ ...s, [userId + '_role']: false }));
  }

  async function updateAccess(userId, agentIds) {
    setSaving(s => ({ ...s, [userId + '_access']: true }));
    try {
      const res = await fetch(`${BACKEND}/api/admin/users/${userId}/access`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentIds)
      });
      if (res.ok) {
        setUsers(prev => prev.map(u => u.user_id === userId ? { ...u, agent_access: agentIds } : u));
      } else alert('Failed to update access');
    } catch (e) { alert('Error updating access'); }
    setSaving(s => ({ ...s, [userId + '_access']: false }));
  }

  function toggleAgentAccess(user, agentId) {
    const current = user.agent_access || [];
    const updated = current.includes(agentId)
      ? current.filter(id => id !== agentId)
      : [...current, agentId];
    updateAccess(user.user_id, updated);
  }

  function grantAll(user) {
    updateAccess(user.user_id, agents.map(a => a.agent_id));
  }

  function revokeAll(user) {
    updateAccess(user.user_id, []);
  }

  const filtered = users.filter(u =>
    u.name?.toLowerCase().includes(search.toLowerCase()) ||
    u.email?.toLowerCase().includes(search.toLowerCase())
  );

  const adminCount = users.filter(u => u.role === 'admin').length;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
              User Management
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">
              {users.length} user{users.length !== 1 ? 's' : ''} · {adminCount} admin{adminCount !== 1 ? 's' : ''}
            </p>
          </div>
          <button onClick={fetchAll} className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name or email..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 text-slate-400">
            <Users className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p>No users found</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map(user => {
              const isExpanded = expandedUser === user.user_id;
              const accessCount = (user.agent_access || []).length;
              const isAdmin = user.role === 'admin';

              return (
                <div key={user.user_id} className="bg-white rounded-lg border border-slate-200 overflow-hidden">
                  {/* User row */}
                  <div className="flex items-center gap-4 p-4">
                    {/* Avatar */}
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0 ${
                      isAdmin ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {(user.name || user.email || '?')[0].toUpperCase()}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-900 truncate">{user.name || 'Unknown'}</span>
                        {isAdmin && (
                          <span className="flex-shrink-0 px-1.5 py-0.5 bg-blue-50 text-blue-700 text-xs rounded font-medium">Admin</span>
                        )}
                      </div>
                      <p className="text-sm text-slate-400 truncate">{user.email}</p>
                    </div>

                    {/* Access count (non-admins) */}
                    {!isAdmin && (
                      <span className="text-sm text-slate-500 flex-shrink-0">
                        {accessCount}/{agents.length} agents
                      </span>
                    )}

                    {/* Role toggle */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {isAdmin ? (
                        <button
                          onClick={() => updateRole(user.user_id, 'user')}
                          disabled={saving[user.user_id + '_role']}
                          className="flex items-center gap-1.5 py-1.5 px-3 border border-orange-200 text-orange-600 rounded-md hover:bg-orange-50 text-xs font-medium disabled:opacity-50 transition-colors"
                        >
                          <ShieldOff className="w-3.5 h-3.5" />
                          {saving[user.user_id + '_role'] ? 'Saving...' : 'Demote'}
                        </button>
                      ) : (
                        <button
                          onClick={() => updateRole(user.user_id, 'admin')}
                          disabled={saving[user.user_id + '_role']}
                          className="flex items-center gap-1.5 py-1.5 px-3 border border-blue-200 text-blue-600 rounded-md hover:bg-blue-50 text-xs font-medium disabled:opacity-50 transition-colors"
                        >
                          <Shield className="w-3.5 h-3.5" />
                          {saving[user.user_id + '_role'] ? 'Saving...' : 'Make Admin'}
                        </button>
                      )}

                      {/* Expand for access management (non-admins) */}
                      {!isAdmin && agents.length > 0 && (
                        <button
                          onClick={() => setExpandedUser(isExpanded ? null : user.user_id)}
                          className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-md transition-colors"
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Agent access panel */}
                  {!isAdmin && isExpanded && (
                    <div className="border-t border-slate-100 px-4 pb-4 pt-3">
                      <div className="flex items-center justify-between mb-3">
                        <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Agent Access</p>
                        <div className="flex gap-2">
                          <button
                            onClick={() => grantAll(user)}
                            disabled={saving[user.user_id + '_access']}
                            className="text-xs text-blue-600 hover:underline disabled:opacity-50"
                          >
                            Grant All
                          </button>
                          <span className="text-slate-300">·</span>
                          <button
                            onClick={() => revokeAll(user)}
                            disabled={saving[user.user_id + '_access']}
                            className="text-xs text-red-500 hover:underline disabled:opacity-50"
                          >
                            Revoke All
                          </button>
                        </div>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {agents.map(agent => {
                          const hasAccess = (user.agent_access || []).includes(agent.agent_id);
                          return (
                            <button
                              key={agent.agent_id}
                              onClick={() => toggleAgentAccess(user, agent.agent_id)}
                              disabled={saving[user.user_id + '_access']}
                              className={`flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-all disabled:opacity-50 ${
                                hasAccess
                                  ? 'bg-blue-50 border-blue-200 text-blue-800'
                                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300'
                              }`}
                            >
                              {hasAccess
                                ? <CheckSquare className="w-4 h-4 text-blue-600 flex-shrink-0" />
                                : <Square className="w-4 h-4 text-slate-400 flex-shrink-0" />
                              }
                              <span className="text-sm font-medium truncate">{agent.name}</span>
                            </button>
                          );
                        })}
                      </div>
                      {saving[user.user_id + '_access'] && (
                        <p className="text-xs text-slate-400 mt-2">Saving...</p>
                      )}
                    </div>
                  )}

                  {/* Admin note */}
                  {isAdmin && isExpanded && (
                    <div className="border-t border-slate-100 px-4 py-3">
                      <p className="text-sm text-slate-400">Admins have access to all agents automatically.</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
