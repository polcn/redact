import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ConfigEditor } from '../components/Config/ConfigEditor';
import { useAuth } from '../contexts/AuthContext';

export const Config: React.FC = () => {
  const navigate = useNavigate();
  const { signOut } = useAuth();

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate('/login');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  return (
    <div className="min-h-screen bg-secondary">
      <nav className="nav-anthropic">
        <div className="container-anthropic">
          <div className="flex justify-between">
            <div className="flex items-center">
              <h1 className="text-primary" style={{ fontSize: 'var(--font-size-lg)', fontWeight: 500 }}>
                Document Redaction
              </h1>
            </div>
            <div className="flex items-center gap-md">
              <button
                onClick={() => navigate('/dashboard')}
                className="btn-anthropic btn-anthropic-primary"
              >
                Proceed to Upload →
              </button>
              <button
                onClick={handleSignOut}
                className="btn-anthropic btn-anthropic-secondary"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="container-anthropic" style={{ paddingTop: 'var(--space-3xl)', paddingBottom: 'var(--space-3xl)' }}>
        <div className="fade-in">
          <ConfigEditor />
        </div>
      </main>
    </div>
  );
};