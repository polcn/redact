import React, { useState, useEffect } from 'react';
import { listUserFiles } from '../../services/api';
import { FileItem } from './FileItem';

export interface FileData {
  id: string;
  filename: string;
  status: 'processing' | 'completed' | 'quarantined';
  size: number;
  last_modified: string;
  download_url?: string;
}

export const FileList: React.FC = () => {
  const [files, setFiles] = useState<FileData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadFiles = async () => {
    try {
      setError('');
      const response = await listUserFiles();
      setFiles(response.files || []);
    } catch (err: any) {
      setError('Failed to load files');
      console.error('Error loading files:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFiles();
    // Refresh every 10 seconds to check for status updates
    const interval = setInterval(loadFiles, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center p-xl">
        <div className="spinner-anthropic"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-md" style={{ 
        background: 'rgba(214, 69, 69, 0.1)', 
        border: '1px solid rgba(214, 69, 69, 0.2)',
        borderRadius: 'var(--radius-md)',
        color: '#D64545'
      }}>
        {error}
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="text-center p-xl text-secondary">
        No files uploaded yet
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
      {files.map((file) => (
        <FileItem key={file.id} file={file} />
      ))}
    </div>
  );
};