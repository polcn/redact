import React, { useState } from 'react';
import { Upload } from '../components/Files/Upload';
import { FileList } from '../components/Files/FileList';
import { Navigation } from '../components/Navigation/Navigation';

export const Documents: React.FC = () => {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleUploadComplete = () => {
    // Force refresh of file list
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-secondary">
      <Navigation />

      <main className="container-anthropic" style={{ paddingTop: 'var(--space-3xl)', paddingBottom: 'var(--space-3xl)' }}>
        <div className="fade-in">
          <div style={{ marginBottom: 'var(--space-2xl)' }}>
            <h2 style={{ fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-md)' }}>
              Document Management
            </h2>
            <p className="text-secondary" style={{ fontSize: 'var(--font-size-md)' }}>
              Upload new documents or manage your existing files
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2xl)' }}>
            {/* Upload Section */}
            <div className="card-anthropic" style={{ padding: 'var(--space-xl)' }}>
              <h3 className="mb-lg" style={{ fontSize: 'var(--font-size-lg)' }}>Upload New Document</h3>
              <Upload onUploadComplete={handleUploadComplete} />
            </div>

            {/* File List Section */}
            <div>
              <h3 className="mb-lg" style={{ fontSize: 'var(--font-size-lg)' }}>Your Documents</h3>
              <FileList key={refreshKey} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};