import React from 'react';
import { Navigation } from '../components/Navigation/Navigation';
import QuarantineList from '../components/Quarantine/QuarantineList';

export const Quarantine: React.FC = () => {
  return (
    <div className="min-h-screen bg-secondary">
      <Navigation />

      <main className="container-anthropic" style={{ paddingTop: 'var(--space-3xl)', paddingBottom: 'var(--space-3xl)' }}>
        <div className="fade-in">
          <div style={{ marginBottom: 'var(--space-2xl)' }}>
            <h2 style={{ fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-md)' }}>
              Quarantine Management
            </h2>
            <p className="text-secondary" style={{ fontSize: 'var(--font-size-md)' }}>
              Manage files that failed processing due to security or format issues
            </p>
          </div>

          <QuarantineList />

          <div 
            className="card-anthropic" 
            style={{ 
              marginTop: 'var(--space-2xl)', 
              padding: 'var(--space-xl)',
              backgroundColor: 'var(--accent-orange-hover)',
              border: '1px solid var(--accent-orange)'
            }}
          >
            <div style={{ display: 'flex', gap: 'var(--space-md)' }}>
              <span style={{ fontSize: '1.5rem' }}>🛡️</span>
              <div>
                <h4 style={{ fontSize: 'var(--font-size-md)', fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
                  About Quarantined Files
                </h4>
                <ul style={{ listStyle: 'disc', listStylePosition: 'inside', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
                  <li>Files are quarantined when they contain potential security threats or unsupported formats</li>
                  <li>These files cannot be processed and should be reviewed before deletion</li>
                  <li>Deleted files are permanently removed and cannot be recovered</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};