import React, { useState, useCallback, useRef, useEffect } from 'react';
import { uploadFile } from '../../services/api';

interface UploadProps {
  onUploadComplete: () => void;
}

interface UploadProgress {
  filename: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  message?: string;
}

export const Upload: React.FC<UploadProps> = ({ onUploadComplete }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uploadProgress, setUploadProgress] = useState<UploadProgress[]>([]);
  const [, forceUpdate] = useState({});
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Debug effect to log state changes
  useEffect(() => {
    console.log('Upload state changed - uploading:', uploading);
  }, [uploading]);

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
      handleMultipleFileUpload(files);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log('handleFileSelect called');
    const files = e.target.files;
    console.log('Files selected:', files);
    if (files && files.length > 0) {
      console.log('Calling handleMultipleFileUpload with', files.length, 'files');
      handleMultipleFileUpload(Array.from(files));
      // Reset the input so the same file can be selected again
      e.target.value = '';
    }
  };

  const validateFile = (file: File): string | null => {
    const allowedTypes = ['txt', 'pdf', 'docx', 'doc', 'xlsx', 'xls', 'csv', 'md', 'pptx', 'ppt'];
    const fileExt = file.name.split('.').pop()?.toLowerCase();
    
    if (!fileExt || !allowedTypes.includes(fileExt)) {
      return `Invalid file type. Allowed: ${allowedTypes.join(', ')}`;
    }

    // Validate file size (50MB max)
    if (file.size > 50 * 1024 * 1024) {
      return 'File too large. Maximum size is 50MB.';
    }

    return null;
  };

  const handleMultipleFileUpload = useCallback(async (files: File[]) => {
    console.log('handleMultipleFileUpload started with', files.length, 'files');
    setError('');
    setSuccess('');
    setUploading(true);
    setUploadProgress([]);
    
    try {

    // Validate all files first
    const validFiles: File[] = [];
    const progress: UploadProgress[] = [];

    files.forEach(file => {
      const error = validateFile(file);
      if (error) {
        progress.push({ filename: file.name, status: 'error', message: error });
      } else {
        validFiles.push(file);
        progress.push({ filename: file.name, status: 'pending' });
      }
    });

    setUploadProgress(progress);

    // Upload valid files
    let successCount = 0;
    let errorCount = progress.filter(p => p.status === 'error').length;

    for (let i = 0; i < validFiles.length; i++) {
      const file = validFiles[i];
      const progressIndex = progress.findIndex(p => p.filename === file.name);
      
      // Update progress to uploading
      setUploadProgress(prev => {
        const newProgress = [...prev];
        newProgress[progressIndex].status = 'uploading';
        return newProgress;
      });

      try {
        console.log('Uploading file:', file.name, 'Size:', file.size);
        const response = await uploadFile(file);
        console.log('Upload response:', response);
        successCount++;
        
        // Update progress to success
        setUploadProgress(prev => {
          const newProgress = [...prev];
          newProgress[progressIndex].status = 'success';
          newProgress[progressIndex].message = 'Uploaded';
          return newProgress;
        });
      } catch (err: any) {
        console.error('Upload error for file:', file.name, err);
        console.error('Error response:', err.response);
        console.error('Error message:', err.message);
        errorCount++;
        
        // Update progress to error
        setUploadProgress(prev => {
          const newProgress = [...prev];
          newProgress[progressIndex].status = 'error';
          newProgress[progressIndex].message = err.response?.data?.error || err.message || 'Upload failed';
          return newProgress;
        });
      }
    }

    // Always set uploading to false when done
    setUploading(false);
    forceUpdate({});  // Force re-render
    console.log('Setting uploading to false');

    // Show summary
    console.log('Upload complete - Success:', successCount, 'Errors:', errorCount);
    if (successCount > 0 && errorCount === 0) {
      setSuccess(`Successfully uploaded ${successCount} file${successCount > 1 ? 's' : ''}`);
      // Refresh the file list immediately
      onUploadComplete();
      // Clear progress after delay
      setTimeout(() => {
        setSuccess('');
        setUploadProgress([]);
      }, 3000);
    } else if (successCount > 0 && errorCount > 0) {
      setSuccess(`Uploaded ${successCount} file${successCount > 1 ? 's' : ''}, ${errorCount} failed`);
      // Refresh the file list immediately
      onUploadComplete();
      // Clear progress after delay
      setTimeout(() => {
        setSuccess('');
        setUploadProgress([]);
      }, 5000);
    } else if (errorCount > 0 && successCount === 0) {
      setError(`Failed to upload ${errorCount} file${errorCount > 1 ? 's' : ''}`);
      // Clear error after delay
      setTimeout(() => {
        setError('');
        setUploadProgress([]);
      }, 5000);
    }
    } catch (error) {
      console.error('Unexpected error in handleMultipleFileUpload:', error);
      setUploading(false);
      setError('An unexpected error occurred');
      setTimeout(() => {
        setError('');
        setUploadProgress([]);
      }, 5000);
    }
  }, [onUploadComplete]);

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
          ref={fileInputRef}
          type="file"
          className="hidden"
          id="file-upload"
          accept=".txt,.pdf,.docx,.doc,.xlsx,.xls,.csv,.pptx,.ppt,.md"
          onChange={handleFileSelect}
          disabled={uploading}
          multiple
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
          Supported: TXT, PDF, DOCX, XLSX, CSV, PPTX (max 50MB)
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

      {uploadProgress.length > 0 && (
        <div className="mt-lg p-md" style={{
          background: 'var(--color-background)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)'
        }}>
          <h4 className="text-sm font-medium mb-sm">Upload Progress:</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
            {uploadProgress.map((file, index) => (
              <div key={index} className="flex items-center justify-between text-xs">
                <span style={{ 
                  maxWidth: '200px', 
                  overflow: 'hidden', 
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {file.filename}
                </span>
                <span style={{
                  color: file.status === 'success' ? '#52A373' : 
                         file.status === 'error' ? '#D64545' : 
                         file.status === 'uploading' ? '#CC785C' : '#6B7280',
                  fontSize: 'var(--font-size-xs)'
                }}>
                  {file.status === 'pending' && 'Waiting...'}
                  {file.status === 'uploading' && 'Uploading...'}
                  {file.status === 'success' && '✓ Success'}
                  {file.status === 'error' && `✗ ${file.message || 'Failed'}`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};