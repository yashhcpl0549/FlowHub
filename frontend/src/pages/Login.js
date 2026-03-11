import { useNavigate } from 'react-router-dom';
import { Play } from 'lucide-react';
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const GOOGLE_CLIENT_ID = "993912814221-f3jf5332ura7d27h293etubgbtisn0gk.apps.googleusercontent.com";

export default function Login() {
  const navigate = useNavigate();

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/auth/google`,
        { credential: credentialResponse.credential },
        { withCredentials: true }
      );
      navigate('/dashboard', { state: { user: response.data.user } });
    } catch (err) {
      alert(err.response?.data?.detail || 'Login failed. Please try again.');
    }
  };

  const handleGoogleError = function() {
    alert('Google Sign-In failed. Please try again.');
  };

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-slate-200 p-10">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-12 h-12 bg-slate-900 rounded-lg flex items-center justify-center">
                <Play className="w-6 h-6 text-white" strokeWidth={2} />
              </div>
              <h1 className="text-3xl font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Honasa Flow Hub
              </h1>
            </div>
            <p className="text-slate-500 text-base mt-1">Automation Platform</p>
          </div>
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-slate-900 mb-1" style={{ fontFamily: 'Work Sans, sans-serif' }}>
              Welcome back
            </h2>
            <p className="text-slate-500 text-sm">
              Sign in with your Mamaearth Google account.
            </p>
          </div>
          <div className="flex justify-center">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              theme="outline"
              size="large"
              width="320"
            />
          </div>
          <p className="text-center text-xs text-slate-400 mt-6">
            Access restricted to authorised Honasa users only.
          </p>
        </div>
      </div>
    </GoogleOAuthProvider>
  );
}