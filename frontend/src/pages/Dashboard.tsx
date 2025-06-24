import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Upload } from '../components/Files/Upload';
import { FileList } from '../components/Files/FileList';
import { useNavigate } from 'react-router-dom';

export const Dashboard: React.FC = () => {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate('/login');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const handleUploadComplete = () => {
    // Force refresh of file list
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-secondary">
      <nav className="nav-anthropic">
        <div className="container-anthropic">
          <div className="flex justify-between">
            <div className="flex items-center">
              <h1 className="text-primary" style={{ fontSize: 'var(--font-size-lg)', fontWeight: 500 }}>
                Document Upload
              </h1>
            </div>
            <div className="flex items-center gap-md">
              <button
                onClick={() => navigate('/config')}
                className="btn-anthropic btn-anthropic-secondary"
              >
                ← Back to Config
              </button>
              <span className="text-secondary" style={{ fontSize: 'var(--font-size-sm)' }}>
                {user?.signInDetails?.loginId}
              </span>
              <button
                onClick={handleSignOut}
                className="btn-anthropic"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="container-anthropic" style={{ paddingTop: 'var(--space-3xl)', paddingBottom: 'var(--space-3xl)' }}>
        <div className="fade-in">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2xl)' }}>
            <div>
              <h2 className="mb-lg" style={{ fontSize: 'var(--font-size-xl)' }}>Upload Document</h2>
              <Upload onUploadComplete={handleUploadComplete} />
            </div>

            <div>
              <h2 className="mb-lg" style={{ fontSize: 'var(--font-size-xl)' }}>Your Files</h2>
              <FileList key={refreshKey} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};