import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ConfigEditor } from '../components/Config/ConfigEditor';
import { Navigation } from '../components/Navigation/Navigation';

export const Config: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-secondary">
      <Navigation />

      <main className="container-anthropic" style={{ paddingTop: 'var(--space-3xl)', paddingBottom: 'var(--space-3xl)' }}>
        <div className="fade-in">
          <div className="text-center" style={{ marginBottom: 'var(--space-2xl)' }}>
            <h2 style={{ fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-md)' }}>
              Redaction Configuration
            </h2>
            <p className="text-secondary" style={{ fontSize: 'var(--font-size-md)' }}>
              Configure your redaction rules and patterns before processing documents
            </p>
          </div>
          
          <ConfigEditor />

          <div className="text-center" style={{ marginTop: 'var(--space-2xl)' }}>
            <button
              onClick={() => navigate('/documents')}
              className="btn-anthropic btn-anthropic-primary"
              style={{ padding: 'var(--space-md) var(--space-xl)' }}
            >
              Proceed to Documents →
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};