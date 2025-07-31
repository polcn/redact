import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Navigation } from '../components/Navigation/Navigation';

export const Home: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-secondary">
      <Navigation />

      <main>
        {/* Hero Section */}
        <section className="bg-primary text-white" style={{ paddingTop: 'var(--space-2xl)', paddingBottom: 'var(--space-2xl)' }}>
          <div className="container-anthropic">
            <div className="fade-in text-center">
              <h2 style={{ fontSize: 'var(--font-size-2xl)', marginBottom: 'var(--space-lg)' }}>
                Secure Document Redaction
              </h2>
              <p style={{ fontSize: 'var(--font-size-lg)', opacity: 0.9, maxWidth: '600px', margin: '0 auto', marginBottom: 'var(--space-xl)' }}>
                Automatically remove sensitive information from your documents with configurable rules. 
                Supporting PDF, DOCX, XLSX, and TXT formats.
              </p>
              <button
                onClick={() => navigate('/config')}
                className="btn-anthropic"
                style={{ 
                  backgroundColor: 'white', 
                  color: 'var(--color-primary)',
                  padding: 'var(--space-md) var(--space-xl)'
                }}
              >
                Get Started →
              </button>
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section className="container-anthropic" style={{ paddingTop: 'var(--space-2xl)', paddingBottom: 'var(--space-3xl)' }}>
          <div className="fade-in">
            <div className="text-center" style={{ marginBottom: 'var(--space-2xl)' }}>
              <h3 style={{ fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-md)' }}>
                How It Works
              </h3>
            </div>
            
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 'var(--space-xl)' }}>
              <div className="text-center">
                <div style={{ fontSize: '2.5rem', marginBottom: 'var(--space-md)' }}>1️⃣</div>
                <h4 style={{ fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-sm)' }}>Configure Rules</h4>
                <p className="text-secondary">Set up your redaction patterns and replacements</p>
              </div>
              <div className="text-center">
                <div style={{ fontSize: '2.5rem', marginBottom: 'var(--space-md)' }}>2️⃣</div>
                <h4 style={{ fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-sm)' }}>Upload Documents</h4>
                <p className="text-secondary">Upload PDFs, DOCX, XLSX, or TXT files</p>
              </div>
              <div className="text-center">
                <div style={{ fontSize: '2.5rem', marginBottom: 'var(--space-md)' }}>3️⃣</div>
                <h4 style={{ fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-sm)' }}>Download Results</h4>
                <p className="text-secondary">Get your redacted documents instantly</p>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="bg-secondary" style={{ paddingTop: 'var(--space-2xl)', paddingBottom: 'var(--space-2xl)' }}>
          <div className="container-anthropic">
            <div className="fade-in">
              <h3 className="text-center" style={{ fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-xl)' }}>
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
        <section className="text-center" style={{ paddingTop: 'var(--space-2xl)', paddingBottom: 'var(--space-3xl)' }}>
          <div className="container-anthropic">
            <div className="fade-in">
              <h3 style={{ fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-lg)' }}>
                Ready to Get Started?
              </h3>
              <p className="text-secondary" style={{ fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-xl)' }}>
                Start redacting sensitive information from your documents in seconds.
              </p>
              <button
                onClick={() => navigate('/config')}
                className="btn-anthropic btn-anthropic-primary"
                style={{ padding: 'var(--space-md) var(--space-xl)' }}
              >
                Start Now →
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};