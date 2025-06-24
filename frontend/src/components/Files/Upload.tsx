import React, { useState, useCallback } from 'react';
import { uploadFile } from '../../services/api';

interface UploadProps {
  onUploadComplete: () => void;
}

export const Upload: React.FC<UploadProps> = ({ onUploadComplete }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileUpload = async (file: File) => {
    setError('');
    setSuccess('');
    setUploading(true);

    // Validate file type
    const allowedTypes = ['txt', 'pdf', 'docx', 'doc', 'xlsx', 'xls'];
    const fileExt = file.name.split('.').pop()?.toLowerCase();
    
    if (!fileExt || !allowedTypes.includes(fileExt)) {
      setError(`Invalid file type. Allowed: ${allowedTypes.join(', ')}`);
      setUploading(false);
      return;
    }

    // Validate file size (50MB max)
    if (file.size > 50 * 1024 * 1024) {
      setError('File too large. Maximum size is 50MB.');
      setUploading(false);
      return;
    }

    try {
      const response = await uploadFile(file);
      setSuccess(`File uploaded successfully! Document ID: ${response.document_id}`);
      setTimeout(() => {
        setSuccess('');
        onUploadComplete();
      }, 3000);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="w-full">
      <div
        className={`upload-area-anthropic ${isDragging ? 'drag-over' : ''}`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <svg
          className="mx-auto h-12 w-12 text-secondary mb-md"
          stroke="currentColor"
          fill="none"
          viewBox="0 0 48 48"
        >
          <path
            d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        
        <p className="text-secondary" style={{ fontSize: 'var(--font-size-sm)' }}>
          Drop files here or click to upload
        </p>
        
        <input
          type="file"
          className="hidden"
          id="file-upload"
          accept=".txt,.pdf,.docx,.doc,.xlsx,.xls"
          onChange={handleFileSelect}
          disabled={uploading}
        />
        
        <label
          htmlFor="file-upload"
          className={`btn-anthropic btn-anthropic-primary mt-lg ${
            uploading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
          style={{ cursor: uploading ? 'not-allowed' : 'pointer' }}
        >
          {uploading ? 'Uploading...' : 'Select File'}
        </label>
        
        <p className="text-secondary mt-sm" style={{ fontSize: 'var(--font-size-xs)' }}>
          Supported: TXT, PDF, DOCX, XLSX (max 50MB)
        </p>
      </div>

      {error && (
        <div className="mt-lg p-md" style={{ 
          background: 'rgba(214, 69, 69, 0.1)', 
          border: '1px solid rgba(214, 69, 69, 0.2)',
          borderRadius: 'var(--radius-md)',
          color: '#D64545'
        }}>
          {error}
        </div>
      )}

      {success && (
        <div className="mt-lg p-md" style={{ 
          background: 'rgba(82, 163, 115, 0.1)', 
          border: '1px solid rgba(82, 163, 115, 0.2)',
          borderRadius: 'var(--radius-md)',
          color: '#52A373'
        }}>
          {success}
        </div>
      )}
    </div>
  );
};