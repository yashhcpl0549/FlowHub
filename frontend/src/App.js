import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from 'sonner';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import Dashboard from './pages/Dashboard';
import AgentDetail from './pages/AgentDetail';
import JobsList from './pages/JobsList';
import JobDetail from './pages/JobDetail';

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
      <Route path="/jobs" element={<JobsList />} />
      <Route path="/jobs/:jobId" element={<JobDetail />} />
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
