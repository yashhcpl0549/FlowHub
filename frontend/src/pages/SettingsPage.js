import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Key, Check, AlertCircle, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function SettingsPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hasCredentials, setHasCredentials] = useState(false);
  const [credentialsJson, setCredentialsJson] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/users/me`, {
        withCredentials: true
      });
      setUser(response.data);
      setHasCredentials(response.data.has_gcp_credentials || false);
    } catch (error) {
      console.error('Failed to load user:', error);
      navigate('/');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveCredentials = async () => {
    if (!credentialsJson.trim()) {
      toast.error('Please paste your ADC JSON');
      return;
    }

    // Validate JSON
    try {
      const parsed = JSON.parse(credentialsJson);
      if (!parsed.refresh_token && !parsed.private_key) {
        toast.error('Invalid credentials format. Must be an authorized_user or service_account JSON.');
        return;
      }
    } catch (e) {
      toast.error('Invalid JSON format');
      return;
    }

    setSaving(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/users/me/gcp-credentials`,
        { credentials_json: credentialsJson },
        { withCredentials: true }
      );
      toast.success('BigQuery credentials saved successfully!');
      setHasCredentials(true);
      setCredentialsJson('');
    } catch (error) {
      console.error('Failed to save credentials:', error);
      toast.error(error.response?.data?.detail || 'Failed to save credentials');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteCredentials = async () => {
    if (!confirm('Are you sure you want to remove your BigQuery credentials?')) {
      return;
    }

    try {
      await axios.delete(`${BACKEND_URL}/api/users/me/gcp-credentials`, {
        withCredentials: true
      });
      toast.success('Credentials removed');
      setHasCredentials(false);
    } catch (error) {
      console.error('Failed to delete credentials:', error);
      toast.error('Failed to remove credentials');
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
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-semibold text-slate-900 mb-2" style={{ fontFamily: 'Work Sans, sans-serif' }}>
          Settings
        </h1>
        <p className="text-slate-600 mb-8">Manage your account and integrations</p>

        {/* User Info */}
        <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Account</h2>
          <div className="flex items-center gap-4">
            {user?.picture && (
              <img
                src={user.picture}
                alt={user.name}
                className="w-12 h-12 rounded-full"
              />
            )}
            <div>
              <p className="font-medium text-slate-900">{user?.name}</p>
              <p className="text-sm text-slate-600">{user?.email}</p>
            </div>
          </div>
        </div>

        {/* BigQuery Credentials */}
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-cyan-100 rounded-lg flex items-center justify-center">
              <Key className="w-5 h-5 text-cyan-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">BigQuery Credentials</h2>
              <p className="text-sm text-slate-600">Connect your Google Cloud credentials for Data Query Assistant</p>
            </div>
          </div>

          {hasCredentials ? (
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Check className="w-5 h-5 text-emerald-600" />
                  <div>
                    <p className="font-medium text-emerald-900">Credentials Connected</p>
                    <p className="text-sm text-emerald-700">Your BigQuery credentials are configured</p>
                  </div>
                </div>
                <button
                  onClick={handleDeleteCredentials}
                  className="text-red-600 hover:text-red-700 p-2"
                  title="Remove credentials"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium mb-1">How to get your credentials:</p>
                    <ol className="list-decimal list-inside space-y-1">
                      <li>Run <code className="bg-amber-100 px-1 rounded">gcloud auth application-default login</code> in your terminal</li>
                      <li>Open the generated JSON file (usually at <code className="bg-amber-100 px-1 rounded">~/.config/gcloud/application_default_credentials.json</code>)</li>
                      <li>Copy the entire JSON content and paste it below</li>
                    </ol>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Paste your ADC JSON credentials
                </label>
                <textarea
                  value={credentialsJson}
                  onChange={(e) => setCredentialsJson(e.target.value)}
                  placeholder='{"account": "", "client_id": "...", "client_secret": "...", ...}'
                  className="w-full h-40 px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 font-mono text-sm"
                />
              </div>

              <button
                onClick={handleSaveCredentials}
                disabled={saving || !credentialsJson.trim()}
                className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
              >
                {saving ? 'Saving...' : 'Save Credentials'}
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
