import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from 'sonner';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import Dashboard from './pages/Dashboard';
import AgentDetail from './pages/AgentDetail';
import ChatAgentPage from './pages/ChatAgentPage';
import JobsList from './pages/JobsList';
import JobDetail from './pages/JobDetail';
import AdminDashboard from './pages/AdminDashboard';
import ManageUsers from './pages/ManageUsers';
import ManageAgents from './pages/ManageAgents';
import SettingsPage from './pages/SettingsPage';

function AppRouter() {
  const location = useLocation();
  
  // Check URL fragment for session_id BEFORE routing
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }
  
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/agent/:agentId" element={<AgentDetail />} />
      <Route path="/chat/:agentId" element={<ChatAgentPage />} />
      <Route path="/jobs" element={<JobsList />} />
      <Route path="/jobs/:jobId" element={<JobDetail />} />
      <Route path="/admin" element={<AdminDashboard />} />
      <Route path="/admin/users" element={<ManageUsers />} />
      <Route path="/admin/agents" element={<ManageAgents />} />
      <Route path="/settings" element={<SettingsPage />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AppRouter />
        <Toaster position="top-right" richColors />
      </BrowserRouter>
    </div>
  );
}

export default App;
