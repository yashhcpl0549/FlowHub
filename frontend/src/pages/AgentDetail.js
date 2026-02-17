import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { Upload, Play, AlertCircle, FileText, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function AgentDetail() {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [uploadComplete, setUploadComplete] = useState(false);

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
      if (error.response?.status === 401) {
        navigate('/');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);
    setUploadComplete(false);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      toast.error('Please select files to upload');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/agents/${agentId}/upload`,
        formData,
        {
          withCredentials: true,
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );
      
      setJobId(response.data.job_id);
      setUploadComplete(true);
      toast.success('Files uploaded successfully!');
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleExecute = async () => {
    if (!jobId) {
      toast.error('Please upload files first');
      return;
    }

    setExecuting(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/agents/${agentId}/execute`,
        { job_id: jobId },
        { withCredentials: true }
      );
      
      toast.success('Job execution started! You will receive an email when complete.');
      
      // Navigate to job status page after 2 seconds
      setTimeout(() => {
        navigate(`/jobs/${jobId}`);
      }, 2000);
    } catch (error) {
      console.error('Execution failed:', error);
      toast.error(error.response?.data?.detail || 'Execution failed');
      setExecuting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Agent not found</h2>
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
            to="/dashboard"
            className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-slate-900 mb-2" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                {agent.name}
              </h1>
              <p className="text-slate-600 leading-relaxed max-w-3xl">
                {agent.description}
              </p>
            </div>
            <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-md border border-emerald-200">
              Active
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Upload & Execute */}
          <div className="space-y-6">
            {/* Required Files */}
            <div className="bg-white rounded-lg border border-slate-200 p-6 fade-in">
              <h3 className="text-lg font-semibold text-slate-900 mb-4" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Required Input Files
              </h3>
              <div className="space-y-2 mb-6">
                {agent.required_files.map((file, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm text-slate-700">
                    <FileText className="w-4 h-4 text-blue-600" />
                    <span>{file}</span>
                  </div>
                ))}
              </div>
              
              {/* File Upload */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-900 mb-2">
                  Select Files
                </label>
                <div className="file-upload-zone border-2 border-dashed border-slate-300 rounded-lg p-6 text-center">
                  <Upload className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                  <input
                    type="file"
                    multiple
                    onChange={handleFileChange}
                    className="hidden"
                    id="file-input"
                    data-testid="file-input"
                  />
                  <label
                    htmlFor="file-input"
                    className="cursor-pointer text-sm text-slate-600 hover:text-slate-900"
                  >
                    Click to select files or drag and drop
                  </label>
                  {files.length > 0 && (
                    <div className="mt-4 space-y-1">
                      {files.map((file, idx) => (
                        <div key={idx} className="text-sm text-slate-700 flex items-center gap-2 justify-center">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          {file.name}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Upload Button */}
              <button
                onClick={handleUpload}
                disabled={uploading || files.length === 0 || uploadComplete}
                data-testid="upload-btn"
                className="w-full py-3 px-4 bg-slate-900 text-white rounded-md hover:bg-slate-800 disabled:bg-slate-300 disabled:cursor-not-allowed transition-all hover:-translate-y-0.5 active:scale-95 font-medium shadow-sm mb-4"
              >
                {uploading ? 'Uploading...' : uploadComplete ? 'Files Uploaded' : 'Upload Files'}
              </button>

              {/* Execute Button */}
              <button
                onClick={handleExecute}
                disabled={executing || !uploadComplete}
                data-testid="execute-btn"
                className="w-full py-3 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-all hover:-translate-y-0.5 active:scale-95 font-medium shadow-sm flex items-center justify-center gap-2"
              >
                <Play className="w-4 h-4" strokeWidth={2} />
                {executing ? 'Starting Execution...' : 'Execute Agent'}
              </button>
            </div>
          </div>

          {/* Right Column - Info */}
          <div className="space-y-6">
            {/* How it Works */}
            <div className="bg-white rounded-lg border border-slate-200 p-6 fade-in">
              <h3 className="text-lg font-semibold text-slate-900 mb-4" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                How It Works
              </h3>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-blue-50 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-semibold text-blue-600">1</span>
                  </div>
                  <div>
                    <div className="font-medium text-slate-900">Upload Required Files</div>
                    <div className="text-sm text-slate-600">Select and upload all required input files listed above.</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-blue-50 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-semibold text-blue-600">2</span>
                  </div>
                  <div>
                    <div className="font-medium text-slate-900">Input Validation</div>
                    <div className="text-sm text-slate-600">System validates your inputs and checks for missing files or errors.</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-blue-50 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-semibold text-blue-600">3</span>
                  </div>
                  <div>
                    <div className="font-medium text-slate-900">Execute Agent</div>
                    <div className="text-sm text-slate-600">Trigger the automation script to process your data.</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-blue-50 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-semibold text-blue-600">4</span>
                  </div>
                  <div>
                    <div className="font-medium text-slate-900">Receive Results</div>
                    <div className="text-sm text-slate-600">Get output files via email and download from the platform.</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Status Info */}
            {uploadComplete && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-6 fade-in">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium text-emerald-900 mb-1">Files Uploaded Successfully</div>
                    <div className="text-sm text-emerald-700">
                      Job ID: <span className="font-mono">{jobId}</span>
                    </div>
                    <div className="text-sm text-emerald-700 mt-2">
                      Click "Execute Agent" to start processing.
                    </div>
                  </div>
                </div>
              </div>
            )}

            {executing && (
              <div className="bg-sky-50 border border-sky-200 rounded-lg p-6 fade-in">
                <div className="flex items-start gap-3">
                  <div className="loading-spinner w-5 h-5 flex-shrink-0 mt-0.5"></div>
                  <div>
                    <div className="font-medium text-sky-900 mb-1">Processing...</div>
                    <div className="text-sm text-sky-700">
                      Your job is being processed. You'll receive an email notification when complete.
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
