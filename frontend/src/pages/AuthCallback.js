import { useEffect, useState, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function AuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const hasProcessed = useRef(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processSession = async () => {
      try {
        // Extract session_id from URL fragment
        const hash = location.hash;
        const params = new URLSearchParams(hash.substring(1));
        const sessionId = params.get('session_id');

        if (!sessionId) {
          setError('No session ID found');
          setTimeout(() => navigate('/'), 2000);
          return;
        }

        // Exchange session_id for session_token
        const response = await axios.post(
          `${BACKEND_URL}/api/auth/session`,
          { session_id: sessionId },
          { withCredentials: true }
        );

        const user = response.data.user;

        // Redirect to dashboard with user data
        navigate('/dashboard', { state: { user }, replace: true });
      } catch (err) {
        console.error('Auth callback error:', err);
        setError('Authentication failed. Redirecting...');
        setTimeout(() => navigate('/'), 2000);
      }
    };

    processSession();
  }, [location, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center">
        {error ? (
          <div>
            <div className="text-red-600 text-lg font-medium mb-2">{error}</div>
            <div className="text-slate-600">Please try again</div>
          </div>
        ) : (
          <div>
            <div className="loading-spinner mx-auto mb-4"></div>
            <div className="text-slate-900 text-lg font-medium">Authenticating...</div>
            <div className="text-slate-600 mt-2">Please wait</div>
          </div>
        )}
      </div>
    </div>
  );
}
