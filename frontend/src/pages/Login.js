import { useNavigate } from 'react-router-dom';
import { Play } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();

  const handleGoogleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="login-container">
      {/* Left side - Form */}
      <div className="flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md fade-in">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-12 h-12 bg-slate-900 rounded-lg flex items-center justify-center">
                <Play className="w-6 h-6 text-white" strokeWidth={2} />
              </div>
              <h1 className="text-3xl font-semibold text-slate-900" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Honasa Flow Hub
              </h1>
            </div>
            <p className="text-slate-600 text-lg">Automation Platform</p>
          </div>

          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-semibold text-slate-900 mb-2" style={{ fontFamily: 'Work Sans, sans-serif' }}>
                Welcome back
              </h2>
              <p className="text-slate-600">
                Sign in to access your automation agents and manage your workflows.
              </p>
            </div>

            <button
              data-testid="google-login-btn"
              onClick={handleGoogleLogin}
              className="w-full py-3 px-4 bg-slate-900 text-white rounded-md hover:bg-slate-800 transition-all hover:-translate-y-0.5 active:scale-95 font-medium flex items-center justify-center gap-3 shadow-sm"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Continue with Google
            </button>

            <div className="pt-6 border-t border-slate-200">
              <p className="text-sm text-slate-500 text-center">
                By signing in, you agree to our Terms of Service and Privacy Policy
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Image */}
      <div
        className="login-image-section relative overflow-hidden"
        style={{
          backgroundImage: 'url(https://images.unsplash.com/photo-1763929154494-a3d6eba05282?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGdlb21ldHJpYyUyMHRlY2hub2xvZ3klMjB3aGl0ZSUyMGJhY2tncm91bmQlMjBtaW5pbWFsaXN0fGVufDB8fHx8MTc3MTM0NTcyNHww&ixlib=rb-4.1.0&q=85)',
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900/90 to-slate-900/70" />
        <div className="relative h-full flex items-center justify-center p-12">
          <div className="max-w-md text-white">
            <h3 className="text-4xl font-semibold mb-6" style={{ fontFamily: 'Work Sans, sans-serif' }}>
              Automate Your Workflows
            </h3>
            <p className="text-lg text-slate-200 leading-relaxed">
              Transform manual data processing into automated workflows. Upload files, trigger scripts, and receive results instantly.
            </p>
            <div className="mt-8 space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 mt-1">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <div className="font-medium">Multiple Agents</div>
                  <div className="text-slate-300 text-sm">Access various automation scripts for different workflows</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 mt-1">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <div className="font-medium">Instant Processing</div>
                  <div className="text-slate-300 text-sm">Upload inputs and download results directly from the platform</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 mt-1">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <div className="font-medium">Error Validation</div>
                  <div className="text-slate-300 text-sm">Built-in validation ensures data quality before processing</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
