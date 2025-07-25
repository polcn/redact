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
  const [selectedModel, setSelectedModel] = useState<string>('');  // Empty means use default
  const [isGeneratingAI, setIsGeneratingAI] = useState(false);
  
  // Batch AI Summary state
  const [showBatchAIModal, setShowBatchAIModal] = useState(false);
  const [batchSummaryType, setBatchSummaryType] = useState<'brief' | 'standard' | 'detailed'>('standard');
  const [batchModel, setBatchModel] = useState<string>('');  // Empty means use default
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0 });

  const loadFiles = async () => {
    try {
      setError('');
      const response = await listUserFiles();
      console.log('Files loaded:', response.files?.length || 0, 'files');
      setFiles(response.files || []);
    } catch (err: any) {
      setError('Failed to load files');
      console.error('Error loading files:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAISummary = (file: FileData) => {
    console.log('Opening AI Summary modal for:', file.filename);
    setSelectedFileForAI(file);
    setShowAISummaryModal(true);
  };

  const handleGenerateAISummary = async () => {
    if (!selectedFileForAI) return;
    
    console.log('Starting AI summary generation for:', selectedFileForAI.filename);
    setIsGeneratingAI(true);
    try {
      const { generateAISummary } = await import('../../services/api');
      const result = await generateAISummary(selectedFileForAI.id, selectedSummaryType, selectedModel);
      
      console.log('AI Summary result:', result);
      
      // Close modal and refresh the file list to show the new AI summary
      setShowAISummaryModal(false);
      setSelectedFileForAI(null);
      await loadFiles(); // Refresh the file list
    } catch (err: any) {
      console.error('AI Summary Error:', err);
      alert(err.response?.data?.error || err.message || 'Failed to generate AI summary');
    } finally {
      setIsGeneratingAI(false);
    }
  };

  const handleBatchAISummary = async () => {
    console.log('Starting batch AI summary generation');
    setIsBatchProcessing(true);
    setBatchProgress({ current: 0, total: 0 });
    
    try {
      // Get list of selected files that are completed and don't already have AI summaries
      const filesToProcess = files.filter(f => 
        selectedFiles.has(f.id) && 
        f.status === 'completed' &&
        !f.filename.includes('_AI.')
      );
      
      if (filesToProcess.length === 0) {
        setError('No eligible files selected for AI summary');
        setIsBatchProcessing(false);
        return;
      }
      
      setBatchProgress({ current: 0, total: filesToProcess.length });
      
      // Process each file
      const { generateAISummary } = await import('../../services/api');
      let successCount = 0;
      let errorCount = 0;
      
      for (let i = 0; i < filesToProcess.length; i++) {
        const file = filesToProcess[i];
        setBatchProgress({ current: i + 1, total: filesToProcess.length });
        
        try {
          console.log(`Processing file ${i + 1}/${filesToProcess.length}: ${file.filename}`);
          await generateAISummary(file.id, batchSummaryType, batchModel);
          successCount++;
        } catch (err: any) {
          console.error(`Failed to generate AI summary for ${file.filename}:`, err);
          errorCount++;
        }
      }
      
      // Show results
      if (errorCount > 0) {
        alert(`Batch AI Summary Complete\n\nSuccess: ${successCount}\nFailed: ${errorCount}`);
      } else {
        console.log(`Batch AI summary complete: ${successCount} files processed`);
      }
      
      // Clear selection and close modal
      setSelectedFiles(new Set());
      setShowBatchAIModal(false);
      setBatchSummaryType('standard');
      
      // Refresh the file list to show new AI summaries
      await loadFiles();
      
    } catch (err: any) {
      console.error('Batch AI Summary Error:', err);
      alert('Failed to process batch AI summaries');
    } finally {
      setIsBatchProcessing(false);
      setBatchProgress({ current: 0, total: 0 });
    }
  };

  useEffect(() => {
    loadFiles();
    // Refresh every 10 seconds to check for status updates, but not when modals are open
    const interval = setInterval(() => {
      // Don't refresh if any modal is open
      if (!showAISummaryModal && !showCombineModal && !showBatchAIModal) {
        loadFiles();
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [showAISummaryModal, showCombineModal, showBatchAIModal]);

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
      console.log('Calling combineFiles API...');
      const response = await combineFiles(selectedFileIds, combineFilename);
      console.log('Combine files response:', response);
      
      // Clear selection and close modal
      setSelectedFiles(new Set());
      setShowCombineModal(false);
      setCombineFilename('combined_document.txt');
      
      // Refresh the file list to show the new combined file
      console.log('Refreshing file list...');
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
                    onClick={() => setShowBatchAIModal(true)}
                    className="btn-anthropic btn-anthropic-primary"
                    style={{ padding: '0.5rem 1rem' }}
                  >
                    Batch AI Summary
                  </button>
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
          onClick={(e) => {
            // Close modal when clicking backdrop
            console.log('Backdrop clicked - closing modal');
            setShowAISummaryModal(false);
            setSelectedFileForAI(null);
          }}
          style={{
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
          <div 
            onClick={(e) => {
              // Prevent closing when clicking inside modal
              e.stopPropagation();
            }}
            className="card-anthropic" 
            style={{ 
            width: '90%', 
            maxWidth: '500px',
            padding: 'var(--spacing-lg)'
          }}>
            <h2 className="text-primary" style={{ marginBottom: 'var(--spacing-md)' }}>
              Generate AI Summary
            </h2>
            
            <p className="text-secondary" style={{ marginBottom: 'var(--spacing-lg)' }}>
              Select the type of summary you want to generate for "{selectedFileForAI.filename}":
            </p>
            
            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
              <label style={{ display: 'block', marginBottom: 'var(--spacing-sm)' }}>
                Summary Type:
              </label>
              <select 
                value={selectedSummaryType}
                onChange={(e) => setSelectedSummaryType(e.target.value as 'brief' | 'standard' | 'detailed')}
                className="input-anthropic"
                style={{ width: '100%' }}
              >
                <option value="brief">Brief (2-3 sentences)</option>
                <option value="standard">Standard (comprehensive)</option>
                <option value="detailed">Detailed (in-depth analysis)</option>
              </select>
            </div>
            
            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
              <label style={{ display: 'block', marginBottom: 'var(--spacing-sm)' }}>
                AI Model:
              </label>
              <select 
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="input-anthropic"
                style={{ width: '100%' }}
              >
                <option value="">Default (Claude 3 Haiku)</option>
                <optgroup label="Claude Models">
                  <option value="anthropic.claude-3-haiku-20240307-v1:0">Claude 3 Haiku (Fast)</option>
                  <option value="anthropic.claude-3-5-haiku-20241022-v1:0">Claude 3.5 Haiku (Latest Fast)</option>
                  <option value="anthropic.claude-3-sonnet-20240229-v1:0">Claude 3 Sonnet</option>
                  <option value="anthropic.claude-3-5-sonnet-20241022-v2:0">Claude 3.5 Sonnet (Latest)</option>
                  <option value="anthropic.claude-3-opus-20240229-v1:0">Claude 3 Opus (Most Capable)</option>
                </optgroup>
                <optgroup label="Amazon Nova (Free Tier)">
                  <option value="amazon.nova-micro-v1:0">Nova Micro (Fastest, Free)</option>
                  <option value="amazon.nova-lite-v1:0">Nova Lite (Balanced, Free)</option>
                  <option value="amazon.nova-pro-v1:0">Nova Pro (Advanced, Free)</option>
                </optgroup>
                <optgroup label="Meta Llama">
                  <option value="meta.llama3-2-1b-instruct-v1:0">Llama 3.2 1B (Tiny)</option>
                  <option value="meta.llama3-2-3b-instruct-v1:0">Llama 3.2 3B (Small)</option>
                  <option value="meta.llama3-8b-instruct-v1:0">Llama 3 8B (Medium)</option>
                </optgroup>
                <optgroup label="Mistral">
                  <option value="mistral.mistral-7b-instruct-v0:2">Mistral 7B</option>
                  <option value="mistral.mistral-small-2402-v1:0">Mistral Small</option>
                </optgroup>
                <optgroup label="DeepSeek">
                  <option value="deepseek.r1-v1:0">DeepSeek R1 (Advanced Reasoning)</option>
                </optgroup>
                <optgroup label="OpenAI (Requires API Key)">
                  <option value="openai.gpt-4o">GPT-4o (Most Capable)</option>
                  <option value="openai.gpt-4o-mini">GPT-4o Mini (Fast & Cheap)</option>
                  <option value="openai.gpt-4-turbo">GPT-4 Turbo</option>
                  <option value="openai.gpt-3.5-turbo">GPT-3.5 Turbo (Legacy)</option>
                </optgroup>
                <optgroup label="Google Gemini (Requires API Key)">
                  <option value="gemini.gemini-1.5-pro">Gemini 1.5 Pro (Advanced)</option>
                  <option value="gemini.gemini-1.5-flash">Gemini 1.5 Flash (Fast)</option>
                  <option value="gemini.gemini-1.0-pro">Gemini 1.0 Pro (Stable)</option>
                </optgroup>
              </select>
            </div>
            
            <div style={{ display: 'flex', gap: 'var(--spacing-md)', justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setShowAISummaryModal(false);
                  setSelectedFileForAI(null);
                }}
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

      {/* Batch AI Summary Modal */}
      {showBatchAIModal && (
        <div 
          onClick={(e) => {
            setShowBatchAIModal(false);
          }}
          style={{
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
          }}
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            style={{ 
              width: '90%', 
              maxWidth: '550px',
              background: 'white',
              borderRadius: '8px',
              padding: '32px',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
              border: '1px solid #e0e0e0'
            }}
          >
            <h2 style={{ 
              fontSize: '1.5rem',
              fontWeight: '600',
              color: '#1a1a1a',
              marginBottom: '20px'
            }}>
              Batch AI Summary
            </h2>
            
            <p style={{ 
              fontSize: '0.95rem',
              color: '#666',
              marginBottom: '24px',
              lineHeight: '1.5'
            }}>
              Generate AI summaries for {files.filter(f => selectedFiles.has(f.id) && f.status === 'completed' && !f.filename.includes('_AI.')).length} selected files.
            </p>
            
            {isBatchProcessing && (
              <div style={{ marginBottom: '24px' }}>
                <div style={{ 
                  marginBottom: '8px',
                  fontSize: '0.9rem',
                  color: '#555'
                }}>
                  Progress: {batchProgress.current} / {batchProgress.total}
                </div>
                <div style={{
                  width: '100%',
                  height: '20px',
                  background: '#f5f5f5',
                  borderRadius: '10px',
                  overflow: 'hidden',
                  border: '1px solid #e0e0e0'
                }}>
                  <div style={{
                    width: `${batchProgress.total > 0 ? (batchProgress.current / batchProgress.total) * 100 : 0}%`,
                    height: '100%',
                    background: 'linear-gradient(90deg, #4F90F0 0%, #3B82F6 100%)',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>
            )}
            
            <div style={{ marginBottom: '20px' }}>
              <label style={{ 
                display: 'block', 
                marginBottom: '8px',
                fontSize: '0.9rem',
                fontWeight: '500',
                color: '#333'
              }}>
                Summary Type:
              </label>
              <select 
                value={batchSummaryType}
                onChange={(e) => setBatchSummaryType(e.target.value as 'brief' | 'standard' | 'detailed')}
                style={{ 
                  width: '100%',
                  padding: '10px 12px',
                  fontSize: '0.95rem',
                  border: '1px solid #ddd',
                  borderRadius: '6px',
                  background: 'white',
                  cursor: isBatchProcessing ? 'not-allowed' : 'pointer'
                }}
                disabled={isBatchProcessing}
              >
                <option value="brief">Brief (2-3 sentences)</option>
                <option value="standard">Standard (comprehensive)</option>
                <option value="detailed">Detailed (in-depth analysis)</option>
              </select>
            </div>
            
            <div style={{ marginBottom: '24px' }}>
              <label style={{ 
                display: 'block', 
                marginBottom: '8px',
                fontSize: '0.9rem',
                fontWeight: '500',
                color: '#333'
              }}>
                AI Model:
              </label>
              <select 
                value={batchModel}
                onChange={(e) => setBatchModel(e.target.value)}
                style={{ 
                  width: '100%',
                  padding: '10px 12px',
                  fontSize: '0.95rem',
                  border: '1px solid #ddd',
                  borderRadius: '6px',
                  background: 'white',
                  cursor: isBatchProcessing ? 'not-allowed' : 'pointer'
                }}
                disabled={isBatchProcessing}
              >
                <option value="">Default (Claude 3 Haiku)</option>
                <optgroup label="Claude Models">
                  <option value="anthropic.claude-3-haiku-20240307-v1:0">Claude 3 Haiku (Fast)</option>
                  <option value="anthropic.claude-3-5-haiku-20241022-v1:0">Claude 3.5 Haiku (Latest Fast)</option>
                  <option value="anthropic.claude-3-sonnet-20240229-v1:0">Claude 3 Sonnet</option>
                  <option value="anthropic.claude-3-5-sonnet-20241022-v2:0">Claude 3.5 Sonnet (Latest)</option>
                  <option value="anthropic.claude-3-opus-20240229-v1:0">Claude 3 Opus (Most Capable)</option>
                </optgroup>
                <optgroup label="Amazon Nova (Free Tier)">
                  <option value="amazon.nova-micro-v1:0">Nova Micro (Fastest, Free)</option>
                  <option value="amazon.nova-lite-v1:0">Nova Lite (Balanced, Free)</option>
                  <option value="amazon.nova-pro-v1:0">Nova Pro (Advanced, Free)</option>
                </optgroup>
                <optgroup label="Meta Llama">
                  <option value="meta.llama3-2-1b-instruct-v1:0">Llama 3.2 1B (Tiny)</option>
                  <option value="meta.llama3-2-3b-instruct-v1:0">Llama 3.2 3B (Small)</option>
                  <option value="meta.llama3-8b-instruct-v1:0">Llama 3 8B (Medium)</option>
                </optgroup>
                <optgroup label="Mistral">
                  <option value="mistral.mistral-7b-instruct-v0:2">Mistral 7B</option>
                  <option value="mistral.mistral-small-2402-v1:0">Mistral Small</option>
                </optgroup>
                <optgroup label="DeepSeek">
                  <option value="deepseek.r1-v1:0">DeepSeek R1 (Advanced Reasoning)</option>
                </optgroup>
                <optgroup label="OpenAI (Requires API Key)">
                  <option value="openai.gpt-4o">GPT-4o (Most Capable)</option>
                  <option value="openai.gpt-4o-mini">GPT-4o Mini (Fast & Cheap)</option>
                  <option value="openai.gpt-4-turbo">GPT-4 Turbo</option>
                  <option value="openai.gpt-3.5-turbo">GPT-3.5 Turbo (Legacy)</option>
                </optgroup>
                <optgroup label="Google Gemini (Requires API Key)">
                  <option value="gemini.gemini-1.5-pro">Gemini 1.5 Pro (Advanced)</option>
                  <option value="gemini.gemini-1.5-flash">Gemini 1.5 Flash (Fast)</option>
                  <option value="gemini.gemini-1.0-pro">Gemini 1.0 Pro (Stable)</option>
                </optgroup>
              </select>
            </div>
            
            <div style={{ 
              display: 'flex', 
              gap: '12px', 
              justifyContent: 'flex-end',
              marginTop: '32px'
            }}>
              <button
                onClick={() => setShowBatchAIModal(false)}
                className="btn-anthropic btn-anthropic-secondary"
                disabled={isBatchProcessing}
              >
                Cancel
              </button>
              <button
                onClick={handleBatchAISummary}
                className="btn-anthropic btn-anthropic-primary"
                disabled={isBatchProcessing}
              >
                {isBatchProcessing ? 'Processing...' : 'Generate Summaries'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};