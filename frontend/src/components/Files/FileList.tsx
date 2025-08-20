import React, { useState, useEffect } from 'react';
import { listUserFiles, deleteFile, batchDownloadFiles, combineFiles } from '../../services/api';
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
  const [showCombineModal, setShowCombineModal] = useState(false);
  const [combineFilename, setCombineFilename] = useState('combined_document.txt');
  const [isCombining, setIsCombining] = useState(false);
  const [sortBy, setSortBy] = useState<'date-desc' | 'date-asc' | 'name-asc' | 'name-desc' | 'status'>('date-desc');
  
  // AI Summary modal state
  const [showAISummaryModal, setShowAISummaryModal] = useState(false);
  const [selectedFileForAI, setSelectedFileForAI] = useState<FileData | null>(null);
  const [selectedSummaryType, setSelectedSummaryType] = useState<'brief' | 'standard' | 'detailed'>('standard');
  const [selectedModel, setSelectedModel] = useState<string>('anthropic.claude-3-haiku-20240307-v1:0');
  const [isGeneratingAI, setIsGeneratingAI] = useState(false);

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

  const handleOpenAISummary = (file: FileData) => {
    setSelectedFileForAI(file);
    setShowAISummaryModal(true);
  };

  const handleGenerateAISummary = async () => {
    if (!selectedFileForAI) return;
    
    setIsGeneratingAI(true);
    try {
      const { generateAISummary } = await import('../../services/api');
      const result = await generateAISummary(selectedFileForAI.id, selectedSummaryType, selectedModel);
      
      // Log the result to debug
      console.log('AI Summary Result:', result);
      
      // Close modal and show success message
      setShowAISummaryModal(false);
      setSelectedFileForAI(null);
      
      // Show success message
      alert(`AI summary generated successfully! File "${result.new_filename}" has been added to your documents.`);
      
      // Don't use the download_url from the result - it might cause navigation
      // Just refresh the file list
      await loadFiles();
    } catch (err: any) {
      console.error('AI Summary Error:', err);
      alert(err.response?.data?.error || err.message || 'Failed to generate AI summary');
    } finally {
      setIsGeneratingAI(false);
    }
  };

  useEffect(() => {
    loadFiles();
    // Refresh every 10 seconds to check for status updates, but not when modals are open
    const interval = setInterval(() => {
      // Don't refresh if any modal is open
      if (!showAISummaryModal && !showCombineModal) {
        loadFiles();
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [showAISummaryModal, showCombineModal]);

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
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      setTimeout(() => document.body.removeChild(link), 100);
      
      // Clear selection after download
      setSelectedFiles(new Set());
      
    } catch (err: any) {
      setError('Failed to download files as ZIP');
      console.error('Batch download error:', err);
    }
  };

  const handleCombineFiles = async () => {
    try {
      setError('');
      setIsCombining(true);
      
      // Get list of selected files that are completed
      const selectedFileIds = files
        .filter(f => selectedFiles.has(f.id) && f.status === 'completed')
        .map(f => f.id);
      
      if (selectedFileIds.length === 0) {
        setError('No completed files selected');
        setIsCombining(false);
        return;
      }
      
      // Call combine API
      const response = await combineFiles(selectedFileIds, combineFilename);
      
      // Download the combined file
      const link = document.createElement('a');
      link.href = response.download_url;
      link.download = response.filename;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      setTimeout(() => document.body.removeChild(link), 100);
      
      // Clear selection and close modal
      setSelectedFiles(new Set());
      setShowCombineModal(false);
      setCombineFilename('combined_document.txt');
      
      // Refresh files list to show the new combined file
      await loadFiles();
      
    } catch (err: any) {
      setError('Failed to combine files');
      console.error('Combine files error:', err);
    } finally {
      setIsCombining(false);
    }
  };

  const selectedCount = selectedFiles.size;
  const hasCompletedFiles = files.some(f => f.status === 'completed' && selectedFiles.has(f.id));

  // Sort files based on selected sort option
  const sortedFiles = [...files].sort((a, b) => {
    switch (sortBy) {
      case 'date-desc':
        return new Date(b.last_modified).getTime() - new Date(a.last_modified).getTime();
      case 'date-asc':
        return new Date(a.last_modified).getTime() - new Date(b.last_modified).getTime();
      case 'name-asc':
        return a.filename.localeCompare(b.filename);
      case 'name-desc':
        return b.filename.localeCompare(a.filename);
      case 'status':
        const statusOrder = { completed: 0, processing: 1, quarantined: 2 };
        return statusOrder[a.status] - statusOrder[b.status];
      default:
        return 0;
    }
  });

  return (
    <div>
      {files.length > 0 && (
        <>
          <div className="mb-sm flex items-center justify-between">
            <div className="flex items-center gap-sm">
              <label className="text-secondary" style={{ fontSize: 'var(--font-size-sm)' }}>
                Sort by:
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                className="input-anthropic"
                style={{ 
                  padding: '0.5rem',
                  fontSize: 'var(--font-size-sm)',
                  minWidth: '180px'
                }}
              >
                <option value="date-desc">Date (Newest first)</option>
                <option value="date-asc">Date (Oldest first)</option>
                <option value="name-asc">Name (A-Z)</option>
                <option value="name-desc">Name (Z-A)</option>
                <option value="status">Status</option>
              </select>
            </div>
          </div>
          
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
                <>
                  <button
                    onClick={() => setShowCombineModal(true)}
                    className="btn-anthropic btn-anthropic-primary"
                    style={{ padding: '0.5rem 1rem' }}
                  >
                    Combine Files
                  </button>
                  <button
                    onClick={handleDownloadSelected}
                    className="btn-anthropic btn-anthropic-accent"
                    style={{ padding: '0.5rem 1rem' }}
                  >
                    Download as ZIP
                  </button>
                </>
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
        </>
      )}
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
        {sortedFiles.map((file) => (
          <div key={file.id} className="relative">
            <div className="flex items-center gap-sm">
              <input
                type="checkbox"
                checked={selectedFiles.has(file.id)}
                onChange={() => handleSelectFile(file.id)}
                style={{ width: '1rem', height: '1rem', cursor: 'pointer' }}
              />
              <div style={{ flex: 1 }}>
                <FileItem 
                  file={file} 
                  onDelete={loadFiles}
                  onOpenAISummary={() => handleOpenAISummary(file)}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {/* Combine Files Modal */}
      {showCombineModal && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => setShowCombineModal(false)}
        >
          <div 
            className="bg-white rounded-lg p-lg shadow-xl max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-xl font-semibold mb-md">Combine Files</h2>
            <p className="text-secondary mb-lg">
              Combine {files.filter(f => selectedFiles.has(f.id) && f.status === 'completed').length} selected files into one document.
            </p>
            
            <div className="mb-lg">
              <label className="block text-sm font-medium mb-xs">Output filename:</label>
              <input
                type="text"
                value={combineFilename}
                onChange={(e) => setCombineFilename(e.target.value)}
                className="input-anthropic w-full"
                placeholder="combined_document.txt"
              />
            </div>
            
            <div className="flex justify-end gap-sm">
              <button
                onClick={() => setShowCombineModal(false)}
                className="btn-anthropic btn-anthropic-secondary"
                disabled={isCombining}
              >
                Cancel
              </button>
              <button
                onClick={handleCombineFiles}
                className="btn-anthropic btn-anthropic-primary"
                disabled={isCombining || !combineFilename.trim()}
              >
                {isCombining ? 'Combining...' : 'Combine'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI Summary Modal */}
      {showAISummaryModal && selectedFileForAI && (
        <div 
          onClick={() => {
            setShowAISummaryModal(false);
            setSelectedFileForAI(null);
          }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem'
          }}
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            className="card-anthropic" 
            style={{ 
              width: '100%',
              maxWidth: '600px',
              maxHeight: '90vh',
              overflowY: 'auto',
              padding: '2rem',
              backgroundColor: 'var(--background-primary, #FFFFFF)',
              borderRadius: 'var(--radius-lg, 12px)',
              boxShadow: 'var(--shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.1))'
            }}
          >
            {/* Modal Header */}
            <div style={{ marginBottom: '1.5rem' }}>
              <h2 className="text-primary" style={{ 
                fontSize: 'var(--font-size-xl, 1.5rem)',
                fontWeight: 500,
                marginBottom: '0.75rem'
              }}>
                Generate AI Summary
              </h2>
              
              <p className="text-secondary" style={{ 
                fontSize: 'var(--font-size-sm, 1rem)',
                lineHeight: 'var(--line-height-relaxed, 1.75)',
                color: 'var(--text-secondary, #666666)'
              }}>
                Configure AI summary generation for <strong>"{selectedFileForAI.filename}"</strong>
              </p>
            </div>
            
            {/* Form Fields Container */}
            <div style={{ marginBottom: '2rem' }}>
              {/* Summary Type Field */}
              <div style={{ marginBottom: '1.5rem' }}>
                <label 
                  htmlFor="summary-type"
                  style={{ 
                    display: 'block', 
                    marginBottom: '0.5rem',
                    fontSize: 'var(--font-size-sm, 1rem)',
                    fontWeight: 500,
                    color: 'var(--text-primary, #191919)'
                  }}
                >
                  Summary Type
                </label>
                <select 
                  id="summary-type"
                  value={selectedSummaryType}
                  onChange={(e) => setSelectedSummaryType(e.target.value as 'brief' | 'standard' | 'detailed')}
                  className="input-anthropic"
                  style={{ 
                    width: '100%',
                    padding: '0.75rem 1rem',
                    fontSize: 'var(--font-size-sm, 1rem)',
                    borderRadius: 'var(--radius-md, 8px)',
                    border: '1px solid var(--border-color, #E5E5E5)',
                    backgroundColor: 'var(--background-primary, #FFFFFF)',
                    transition: 'border-color 0.2s ease',
                    cursor: 'pointer'
                  }}
                  aria-label="Select summary type"
                >
                  <option value="brief">Brief (2-3 sentences)</option>
                  <option value="standard">Standard (comprehensive overview)</option>
                  <option value="detailed">Detailed (in-depth analysis)</option>
                </select>
              </div>
              
              {/* Model Selection Field */}
              <div style={{ marginBottom: '1.5rem' }}>
                <label 
                  htmlFor="ai-model"
                  style={{ 
                    display: 'block', 
                    marginBottom: '0.5rem',
                    fontSize: 'var(--font-size-sm, 1rem)',
                    fontWeight: 500,
                    color: 'var(--text-primary, #191919)'
                  }}
                >
                  AI Model
                </label>
                <select 
                  id="ai-model"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="input-anthropic"
                  style={{ 
                    width: '100%',
                    padding: '0.75rem 1rem',
                    fontSize: 'var(--font-size-sm, 1rem)',
                    borderRadius: 'var(--radius-md, 8px)',
                    border: '1px solid var(--border-color, #E5E5E5)',
                    backgroundColor: 'var(--background-primary, #FFFFFF)',
                    transition: 'border-color 0.2s ease',
                    cursor: 'pointer'
                  }}
                  aria-label="Select AI model"
                >
                  <option value="anthropic.claude-3-haiku-20240307-v1:0">Claude 3 Haiku (Fast & Efficient)</option>
                  <option value="anthropic.claude-3-5-sonnet-20240620-v1:0">Claude 3.5 Sonnet (Most Advanced Available)</option>
                  <option value="anthropic.claude-3-sonnet-20240229-v1:0">Claude 3 Sonnet (Balanced)</option>
                  <option value="anthropic.claude-v2:1">Claude 2.1 (Previous Generation)</option>
                  <option value="anthropic.claude-v2">Claude 2.0 (Previous Generation)</option>
                  <option value="anthropic.claude-instant-v1">Claude Instant (Fastest Response)</option>
                </select>
                <p style={{
                  marginTop: '0.5rem',
                  fontSize: 'var(--font-size-xs, 0.875rem)',
                  color: 'var(--text-secondary, #666666)',
                  fontStyle: 'italic'
                }}>
                  Higher capability models provide better analysis but may take longer to process.
                </p>
              </div>
            </div>
            
            {/* Action Buttons */}
            <div style={{ 
              display: 'flex', 
              gap: '1rem', 
              justifyContent: 'flex-end',
              paddingTop: '1rem',
              borderTop: '1px solid var(--border-color, #E5E5E5)'
            }}>
              <button
                onClick={() => {
                  setShowAISummaryModal(false);
                  setSelectedFileForAI(null);
                  setSelectedSummaryType('standard');
                  setSelectedModel('anthropic.claude-3-haiku-20240307-v1:0');
                }}
                className="btn-anthropic btn-anthropic-secondary"
                disabled={isGeneratingAI}
                style={{
                  padding: '0.75rem 1.5rem',
                  fontSize: 'var(--font-size-sm, 1rem)',
                  fontWeight: 500,
                  borderRadius: 'var(--radius-md, 8px)',
                  transition: 'all 0.2s ease'
                }}
                aria-label="Cancel AI summary generation"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerateAISummary}
                className="btn-anthropic btn-anthropic-primary"
                disabled={isGeneratingAI}
                style={{
                  padding: '0.75rem 1.5rem',
                  fontSize: 'var(--font-size-sm, 1rem)',
                  fontWeight: 500,
                  borderRadius: 'var(--radius-md, 8px)',
                  transition: 'all 0.2s ease',
                  minWidth: '140px'
                }}
                aria-label={isGeneratingAI ? 'Generating summary' : 'Generate summary'}
              >
                {isGeneratingAI ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="spinner-anthropic" style={{ 
                      width: '1rem', 
                      height: '1rem',
                      border: '2px solid rgba(255, 255, 255, 0.3)',
                      borderTopColor: 'white',
                      borderRadius: '50%',
                      animation: 'spin 0.6s linear infinite'
                    }} />
                    Generating...
                  </span>
                ) : (
                  'Generate Summary'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
