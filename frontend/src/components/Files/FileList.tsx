import React, { useState, useEffect } from 'react';
import { listUserFiles, deleteFile, batchDownloadFiles } from '../../services/api';
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
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);

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

  const handleSelectAll = () => {
    if (selectedFiles.size === files.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(files.map(f => f.id)));
    }
  };

  const handleSelectFile = (fileId: string) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(fileId)) {
      newSelected.delete(fileId);
    } else {
      newSelected.add(fileId);
    }
    setSelectedFiles(newSelected);
  };

  const handleBatchDelete = async () => {
    if (selectedFiles.size === 0) return;
    
    if (!window.confirm(`Are you sure you want to delete ${selectedFiles.size} file(s)?`)) {
      return;
    }

    setIsDeleting(true);
    setError('');

    let successCount = 0;
    let errorCount = 0;

    const fileIds = Array.from(selectedFiles);
    for (const fileId of fileIds) {
      try {
        await deleteFile(fileId);
        successCount++;
      } catch (err) {
        errorCount++;
      }
    }

    setIsDeleting(false);
    setSelectedFiles(new Set());

    if (errorCount > 0) {
      setError(`Deleted ${successCount} files, ${errorCount} failed`);
    }

    // Refresh the list
    await loadFiles();
  };

  const handleDownloadSelected = async () => {
    try {
      setError('');
      
      // Get list of selected files that are completed
      const selectedFileIds = files
        .filter(f => selectedFiles.has(f.id) && f.status === 'completed')
        .map(f => f.id);
      
      if (selectedFileIds.length === 0) {
        setError('No completed files selected');
        return;
      }
      
      // Call batch download API
      const response = await batchDownloadFiles(selectedFileIds);
      
      // Download the ZIP file
      const link = document.createElement('a');
      link.href = response.download_url;
      link.download = response.filename || 'redacted_documents.zip';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clear selection after download
      setSelectedFiles(new Set());
      
    } catch (err: any) {
      setError('Failed to download files as ZIP');
      console.error('Batch download error:', err);
    }
  };

  const selectedCount = selectedFiles.size;
  const hasCompletedFiles = files.some(f => f.status === 'completed' && selectedFiles.has(f.id));

  return (
    <div>
      {files.length > 0 && (
        <div className="mb-md flex items-center justify-between" style={{
          padding: '0.75rem',
          background: 'var(--color-background)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)'
        }}>
          <div className="flex items-center gap-md">
            <input
              type="checkbox"
              checked={selectedFiles.size === files.length && files.length > 0}
              onChange={handleSelectAll}
              style={{ width: '1rem', height: '1rem', cursor: 'pointer' }}
            />
            <span className="text-secondary" style={{ fontSize: 'var(--font-size-sm)' }}>
              {selectedCount === 0 ? 'Select all' : `${selectedCount} selected`}
            </span>
          </div>
          
          {selectedCount > 0 && (
            <div className="flex items-center gap-sm">
              {hasCompletedFiles && (
                <button
                  onClick={handleDownloadSelected}
                  className="btn-anthropic btn-anthropic-accent"
                  style={{ padding: '0.5rem 1rem' }}
                >
                  Download as ZIP
                </button>
              )}
              <button
                onClick={handleBatchDelete}
                disabled={isDeleting}
                className="btn-anthropic btn-anthropic-secondary"
                style={{ 
                  padding: '0.5rem 1rem',
                  opacity: isDeleting ? 0.5 : 1,
                  cursor: isDeleting ? 'not-allowed' : 'pointer'
                }}
              >
                {isDeleting ? 'Deleting...' : 'Delete Selected'}
              </button>
            </div>
          )}
        </div>
      )}
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
        {files.map((file) => (
          <div key={file.id} className="relative">
            <div className="flex items-center gap-sm">
              <input
                type="checkbox"
                checked={selectedFiles.has(file.id)}
                onChange={() => handleSelectFile(file.id)}
                style={{ width: '1rem', height: '1rem', cursor: 'pointer' }}
              />
              <div style={{ flex: 1 }}>
                <FileItem file={file} onDelete={loadFiles} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};