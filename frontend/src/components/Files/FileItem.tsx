import React, { useState } from 'react';
import { FileData } from './FileList';
import { deleteFile, generateAISummary } from '../../services/api';

interface FileItemProps {
  file: FileData;
  onDelete?: () => void;
}

export const FileItem: React.FC<FileItemProps> = ({ file, onDelete }) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [isGeneratingAI, setIsGeneratingAI] = useState(false);
  const [showAISummaryModal, setShowAISummaryModal] = useState(false);
  const [selectedSummaryType, setSelectedSummaryType] = useState('standard');
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

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete "${file.filename}"?`)) {
      return;
    }

    setIsDeleting(true);
    setDeleteError('');

    try {
      await deleteFile(file.id);
      if (onDelete) {
        onDelete();
      }
    } catch (err: any) {
      setDeleteError(err.response?.data?.error || 'Failed to delete file');
      setTimeout(() => setDeleteError(''), 3000);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleGenerateAISummary = async () => {
    setIsGeneratingAI(true);
    try {
      const result = await generateAISummary(file.id, selectedSummaryType);
      
      // Download the AI-enhanced file
      if (result.download_url) {
        const link = document.createElement('a');
        link.href = result.download_url;
        link.download = result.new_filename || file.filename.replace(/\.([^.]+)$/, '_AI.$1');
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
      
      setShowAISummaryModal(false);
      if (onDelete) {
        onDelete(); // Refresh the file list
      }
    } catch (err: any) {
      alert(err.response?.data?.error || 'Failed to generate AI summary');
    } finally {
      setIsGeneratingAI(false);
    }
  };

  const hasAISummary = file.filename.includes('_AI');

  return (
    <div className="card-anthropic card-anthropic-hover flex items-center justify-between">
      <div className="flex items-center gap-md">
        <div className="flex-shrink-0">
          {getStatusIcon()}
        </div>
        <div>
          <h3 className="text-primary" style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>
            {file.filename}
            {hasAISummary && (
              <span className="badge-anthropic badge-ai" style={{ marginLeft: '0.5rem', padding: '0.25rem 0.5rem', fontSize: 'var(--font-size-xs)' }}>
                AI
              </span>
            )}
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
          <>
            <button
              onClick={(e) => {
                e.preventDefault();
                const link = document.createElement('a');
                link.href = file.download_url!;
                link.download = file.filename;
                link.style.display = 'none';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
              }}
              className="btn-anthropic btn-anthropic-accent"
              style={{ padding: '0.5rem 1rem' }}
            >
              Download
            </button>
            
            {!hasAISummary && (
              <button
                onClick={() => setShowAISummaryModal(true)}
                className="btn-anthropic btn-anthropic-primary"
                style={{ padding: '0.5rem 1rem' }}
                title="Generate AI Summary"
              >
                AI Summary
              </button>
            )}
          </>
        )}
        
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="btn-anthropic btn-anthropic-secondary"
          style={{ 
            padding: '0.5rem 1rem',
            opacity: isDeleting ? 0.5 : 1,
            cursor: isDeleting ? 'not-allowed' : 'pointer'
          }}
          title="Delete file"
        >
          {isDeleting ? 'Deleting...' : 'Delete'}
        </button>
      </div>
      
      {deleteError && (
        <div style={{
          position: 'absolute',
          bottom: '-30px',
          right: '0',
          background: 'rgba(214, 69, 69, 0.9)',
          color: 'white',
          padding: '0.25rem 0.5rem',
          borderRadius: 'var(--radius-sm)',
          fontSize: 'var(--font-size-xs)',
          whiteSpace: 'nowrap'
        }}>
          {deleteError}
        </div>
      )}
      
      {showAISummaryModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div className="card-anthropic" style={{ 
            width: '90%', 
            maxWidth: '500px',
            padding: 'var(--spacing-lg)'
          }}>
            <h2 className="text-primary" style={{ marginBottom: 'var(--spacing-md)' }}>
              Generate AI Summary
            </h2>
            
            <p className="text-secondary" style={{ marginBottom: 'var(--spacing-lg)' }}>
              Select the type of summary you want to generate for "{file.filename}":
            </p>
            
            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
              <label style={{ display: 'block', marginBottom: 'var(--spacing-sm)' }}>
                Summary Type:
              </label>
              <select 
                value={selectedSummaryType}
                onChange={(e) => setSelectedSummaryType(e.target.value)}
                className="input-anthropic"
                style={{ width: '100%' }}
              >
                <option value="brief">Brief (2-3 sentences)</option>
                <option value="standard">Standard (comprehensive)</option>
                <option value="detailed">Detailed (in-depth analysis)</option>
              </select>
            </div>
            
            <div style={{ display: 'flex', gap: 'var(--spacing-md)', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowAISummaryModal(false)}
                className="btn-anthropic btn-anthropic-secondary"
                disabled={isGeneratingAI}
              >
                Cancel
              </button>
              <button
                onClick={handleGenerateAISummary}
                className="btn-anthropic btn-anthropic-primary"
                disabled={isGeneratingAI}
              >
                {isGeneratingAI ? 'Generating...' : 'Generate Summary'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};