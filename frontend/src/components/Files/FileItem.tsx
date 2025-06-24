import React from 'react';
import { FileData } from './FileList';

interface FileItemProps {
  file: FileData;
}

export const FileItem: React.FC<FileItemProps> = ({ file }) => {
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusIcon = () => {
    switch (file.status) {
      case 'processing':
        return (
          <div className="spinner-anthropic" style={{ width: '1.25rem', height: '1.25rem' }}></div>
        );
      case 'completed':
        return (
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="#52A373">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'quarantined':
        return (
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="#D64545">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
    }
  };

  const getStatusText = () => {
    switch (file.status) {
      case 'processing':
        return 'Processing...';
      case 'completed':
        return 'Completed';
      case 'quarantined':
        return 'Failed';
    }
  };

  return (
    <div className="card-anthropic card-anthropic-hover flex items-center justify-between">
      <div className="flex items-center gap-md">
        <div className="flex-shrink-0">
          {getStatusIcon()}
        </div>
        <div>
          <h3 className="text-primary" style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>
            {file.filename}
          </h3>
          <div className="text-secondary mt-xs" style={{ fontSize: 'var(--font-size-xs)' }}>
            {formatFileSize(file.size)} • {formatDate(file.last_modified)}
          </div>
        </div>
      </div>
      
      <div className="flex items-center gap-md">
        <span className={`badge-anthropic ${
          file.status === 'completed' ? 'badge-completed' :
          file.status === 'processing' ? 'badge-processing' :
          'badge-error'
        }`}>
          {getStatusText()}
        </span>
        
        {file.status === 'completed' && file.download_url && (
          <a
            href={file.download_url}
            download
            className="btn-anthropic btn-anthropic-accent"
            style={{ padding: '0.5rem 1rem' }}
          >
            Download
          </a>
        )}
      </div>
    </div>
  );
};