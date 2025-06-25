import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ConfigEditor } from '../components/Config/ConfigEditor';
import { useAuth } from '../contexts/AuthContext';

export const Home: React.FC = () => {
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
                Document Redaction System
              </h1>
            </div>
            <div className="flex items-center gap-md">
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

      <main>
        {/* Hero Section */}
        <section className="bg-primary text-white" style={{ paddingTop: 'var(--space-3xl)', paddingBottom: 'var(--space-3xl)' }}>
          <div className="container-anthropic">
            <div className="fade-in text-center">
              <h2 style={{ fontSize: 'var(--font-size-2xl)', marginBottom: 'var(--space-lg)' }}>
                Secure Document Redaction
              </h2>
              <p style={{ fontSize: 'var(--font-size-lg)', opacity: 0.9, maxWidth: '600px', margin: '0 auto', marginBottom: 'var(--space-xl)' }}>
                Automatically remove sensitive information from your documents with configurable rules. 
                Supporting PDF, DOCX, XLSX, and TXT formats.
              </p>
              <div className="flex justify-center gap-md">
                <button
                  onClick={() => navigate('/dashboard')}
                  className="btn-anthropic"
                  style={{ 
                    backgroundColor: 'white', 
                    color: 'var(--color-primary)',
                    padding: 'var(--space-md) var(--space-xl)'
                  }}
                >
                  Upload Documents →
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Configuration Section */}
        <section className="container-anthropic" style={{ paddingTop: 'var(--space-3xl)', paddingBottom: 'var(--space-3xl)' }}>
          <div className="fade-in">
            <div className="text-center" style={{ marginBottom: 'var(--space-2xl)' }}>
              <h3 style={{ fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-md)' }}>
                Configure Your Redaction Rules
              </h3>
              <p className="text-secondary" style={{ fontSize: 'var(--font-size-md)' }}>
                Set up your redaction patterns before uploading documents
              </p>
            </div>
            
            <ConfigEditor />
          </div>
        </section>

        {/* Features Section */}
        <section className="bg-secondary" style={{ paddingTop: 'var(--space-3xl)', paddingBottom: 'var(--space-3xl)' }}>
          <div className="container-anthropic">
            <div className="fade-in">
              <h3 className="text-center" style={{ fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-2xl)' }}>
                Key Features
              </h3>
              <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--space-xl)' }}>
                <div className="card-anthropic" style={{ padding: 'var(--space-xl)' }}>
                  <h4 style={{ fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-md)' }}>
                    🔒 Secure Processing
                  </h4>
                  <p className="text-secondary">
                    Your documents are processed in isolation with enterprise-grade security. 
                    Each user only sees their own files.
                  </p>
                </div>
                <div className="card-anthropic" style={{ padding: 'var(--space-xl)' }}>
                  <h4 style={{ fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-md)' }}>
                    📁 Multiple Formats
                  </h4>
                  <p className="text-secondary">
                    Support for PDF, DOCX, XLSX, and TXT files. Upload multiple files at once 
                    with real-time progress tracking.
                  </p>
                </div>
                <div className="card-anthropic" style={{ padding: 'var(--space-xl)' }}>
                  <h4 style={{ fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-md)' }}>
                    ⚡ Fast Processing
                  </h4>
                  <p className="text-secondary">
                    Serverless architecture ensures quick processing times. Most documents are 
                    ready within seconds.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="text-center" style={{ paddingTop: 'var(--space-3xl)', paddingBottom: 'var(--space-3xl)' }}>
          <div className="container-anthropic">
            <div className="fade-in">
              <h3 style={{ fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-lg)' }}>
                Ready to Get Started?
              </h3>
              <p className="text-secondary" style={{ fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-xl)' }}>
                Configure your rules above, then upload your documents for redaction.
              </p>
              <button
                onClick={() => navigate('/dashboard')}
                className="btn-anthropic btn-anthropic-primary"
                style={{ padding: 'var(--space-md) var(--space-xl)' }}
              >
                Go to Document Upload →
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};