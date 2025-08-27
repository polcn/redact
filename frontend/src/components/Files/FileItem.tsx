import React, { useState } from 'react';
import { FileData } from './FileList';
import { deleteFile, extractMetadata } from '../../services/api';

interface FileItemProps {
  file: FileData;
  onDelete?: () => void;
  onOpenAISummary?: () => void;
}

interface MetadataType {
  document_id: string;
  filename: string;
  file_size: number;
  content_type: string;
  created_date: string;
  page_count?: number;
  word_count?: number;
  character_count?: number;
  language?: string;
  author?: string;
  title?: string;
  subject?: string;
  creator?: string;
  producer?: string;
  creation_date?: string;
  modification_date?: string;
  entities?: {
    persons?: string[];
    organizations?: string[];
    locations?: string[];
    dates?: string[];
    emails?: string[];
    phone_numbers?: string[];
    urls?: string[];
  };
  content_analysis?: {
    sentiment?: string;
    key_topics?: string[];
    content_type?: string;
    reading_level?: string;
  };
  processing_info?: {
    extraction_timestamp: string;
    processing_time_ms: number;
    method: string;
  };
}

export const FileItem: React.FC<FileItemProps> = React.memo(({ file, onDelete, onOpenAISummary }) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [showMetadata, setShowMetadata] = useState(false);
  const [metadata, setMetadata] = useState<MetadataType | null>(null);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState(false);
  const [metadataError, setMetadataError] = useState('');
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
      const errorMessage = err.response?.data?.error || err.message || 'Failed to delete file';
      console.error('Delete error:', errorMessage);
      setDeleteError(errorMessage);
      setTimeout(() => setDeleteError(''), 5000);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleExtractMetadata = async () => {
    setIsLoadingMetadata(true);
    setMetadataError('');

    try {
      const response = await extractMetadata(file.id);
      setMetadata(response.metadata);
      setShowMetadata(true);
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to extract metadata';
      console.error('Metadata extraction error:', errorMessage);
      setMetadataError(errorMessage);
      setTimeout(() => setMetadataError(''), 5000);
    } finally {
      setIsLoadingMetadata(false);
    }
  };

  const exportMetadata = (format: 'json' | 'csv') => {
    if (!metadata) return;

    const filename = `${metadata.filename}_metadata.${format}`;
    let content: string;
    let mimeType: string;

    if (format === 'json') {
      content = JSON.stringify(metadata, null, 2);
      mimeType = 'application/json';
    } else {
      // CSV format - flatten metadata to key-value pairs
      const flatData: Array<{key: string, value: string}> = [];
      
      const addToFlat = (obj: any, prefix = '') => {
        Object.entries(obj).forEach(([key, value]) => {
          const fullKey = prefix ? `${prefix}.${key}` : key;
          if (value && typeof value === 'object' && !Array.isArray(value)) {
            addToFlat(value, fullKey);
          } else if (Array.isArray(value)) {
            flatData.push({ key: fullKey, value: value.join('; ') });
          } else {
            flatData.push({ key: fullKey, value: String(value || '') });
          }
        });
      };

      addToFlat(metadata);
      
      const csvContent = [
        'Property,Value',
        ...flatData.map(row => `"${row.key}","${row.value.replace(/"/g, '""')}"`)
      ].join('\n');
      
      content = csvContent;
      mimeType = 'text/csv';
    }

    // Create and download file
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
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
                
                // Method 1: Try using the presigned URL directly
                const link = document.createElement('a');
                // Use the presigned URL directly - it already includes the disposition header
                // Do NOT add another response-content-disposition parameter as it will break the signature
                link.href = file.download_url!;
                link.download = file.filename;
                link.style.display = 'none';
                document.body.appendChild(link);
                
                // Add error handling for failed downloads
                link.onerror = () => {
                  console.error('Download failed, trying alternative method');
                  setDeleteError('Download failed. Please try again.');
                  setTimeout(() => setDeleteError(''), 3000);
                  // Method 2: Open in new tab as fallback
                  window.open(file.download_url!, '_blank');
                };
                
                link.click();
                document.body.removeChild(link);
              }}
              className="btn-anthropic btn-anthropic-accent"
              style={{ padding: '0.5rem 1rem' }}
            >
              Download
            </button>

            <button
              onClick={handleExtractMetadata}
              disabled={isLoadingMetadata}
              className="btn-anthropic btn-anthropic-secondary"
              style={{ 
                padding: '0.5rem 1rem',
                opacity: isLoadingMetadata ? 0.5 : 1,
                cursor: isLoadingMetadata ? 'not-allowed' : 'pointer'
              }}
              title="Extract Metadata"
            >
              {isLoadingMetadata ? 'Extracting...' : 'Metadata'}
            </button>
            
            {!hasAISummary && onOpenAISummary && (
              <button
                onClick={onOpenAISummary}
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

      {metadataError && (
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
          {metadataError}
        </div>
      )}

      {/* Metadata Modal */}
      {showMetadata && metadata && (
        <div 
          onClick={() => setShowMetadata(false)}
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
              maxWidth: '800px',
              maxHeight: '90vh',
              overflowY: 'auto',
              padding: '2rem',
              backgroundColor: 'var(--background-primary, #FFFFFF)',
              borderRadius: 'var(--radius-lg, 12px)',
              boxShadow: 'var(--shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.1))'
            }}
          >
            {/* Modal Header */}
            <div style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color, #E5E5E5)', paddingBottom: '1rem' }}>
              <h2 className="text-primary" style={{ 
                fontSize: 'var(--font-size-xl, 1.5rem)',
                fontWeight: 500,
                marginBottom: '0.5rem'
              }}>
                Document Metadata
              </h2>
              <p className="text-secondary" style={{ 
                fontSize: 'var(--font-size-sm, 1rem)',
                color: 'var(--text-secondary, #666666)'
              }}>
                {metadata.filename}
              </p>
            </div>
            
            {/* Basic Information */}
            <div style={{ marginBottom: '2rem' }}>
              <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 500, marginBottom: '1rem', color: 'var(--text-primary)' }}>
                Basic Information
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <strong>File Size:</strong> {formatFileSize(metadata.file_size || 0)}
                </div>
                <div>
                  <strong>Content Type:</strong> {metadata.content_type || 'Unknown'}
                </div>
                <div>
                  <strong>Created:</strong> {formatDate(metadata.created_date)}
                </div>
                {metadata.page_count && (
                  <div>
                    <strong>Pages:</strong> {metadata.page_count}
                  </div>
                )}
                {metadata.word_count && (
                  <div>
                    <strong>Words:</strong> {metadata.word_count.toLocaleString()}
                  </div>
                )}
                {metadata.character_count && (
                  <div>
                    <strong>Characters:</strong> {metadata.character_count.toLocaleString()}
                  </div>
                )}
                {metadata.language && (
                  <div>
                    <strong>Language:</strong> {metadata.language}
                  </div>
                )}
              </div>
            </div>

            {/* Document Properties */}
            {(metadata.author || metadata.title || metadata.subject || metadata.creator || metadata.producer) && (
              <div style={{ marginBottom: '2rem' }}>
                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 500, marginBottom: '1rem', color: 'var(--text-primary)' }}>
                  Document Properties
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  {metadata.title && (
                    <div>
                      <strong>Title:</strong> {metadata.title}
                    </div>
                  )}
                  {metadata.author && (
                    <div>
                      <strong>Author:</strong> {metadata.author}
                    </div>
                  )}
                  {metadata.subject && (
                    <div>
                      <strong>Subject:</strong> {metadata.subject}
                    </div>
                  )}
                  {metadata.creator && (
                    <div>
                      <strong>Creator:</strong> {metadata.creator}
                    </div>
                  )}
                  {metadata.producer && (
                    <div>
                      <strong>Producer:</strong> {metadata.producer}
                    </div>
                  )}
                  {metadata.creation_date && (
                    <div>
                      <strong>Creation Date:</strong> {formatDate(metadata.creation_date)}
                    </div>
                  )}
                  {metadata.modification_date && (
                    <div>
                      <strong>Modified:</strong> {formatDate(metadata.modification_date)}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Entities */}
            {metadata.entities && typeof metadata.entities === 'object' && Object.values(metadata.entities).some(arr => Array.isArray(arr) && arr.length > 0) && (
              <div style={{ marginBottom: '2rem' }}>
                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 500, marginBottom: '1rem', color: 'var(--text-primary)' }}>
                  Extracted Entities
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1rem' }}>
                  {metadata.entities.persons && metadata.entities.persons.length > 0 && (
                    <div>
                      <strong>Persons:</strong>
                      <div style={{ marginTop: '0.5rem' }}>
                        {metadata.entities.persons.map((person, idx) => (
                          <span key={idx} style={{ 
                            display: 'inline-block', 
                            background: 'var(--color-accent, #E3F2FD)', 
                            padding: '0.25rem 0.5rem', 
                            borderRadius: 'var(--radius-sm)', 
                            margin: '0.25rem 0.25rem 0 0',
                            fontSize: 'var(--font-size-sm)'
                          }}>
                            {person}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {metadata.entities.organizations && metadata.entities.organizations.length > 0 && (
                    <div>
                      <strong>Organizations:</strong>
                      <div style={{ marginTop: '0.5rem' }}>
                        {metadata.entities.organizations.map((org, idx) => (
                          <span key={idx} style={{ 
                            display: 'inline-block', 
                            background: 'var(--color-accent, #E3F2FD)', 
                            padding: '0.25rem 0.5rem', 
                            borderRadius: 'var(--radius-sm)', 
                            margin: '0.25rem 0.25rem 0 0',
                            fontSize: 'var(--font-size-sm)'
                          }}>
                            {org}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {metadata.entities.locations && metadata.entities.locations.length > 0 && (
                    <div>
                      <strong>Locations:</strong>
                      <div style={{ marginTop: '0.5rem' }}>
                        {metadata.entities.locations.map((loc, idx) => (
                          <span key={idx} style={{ 
                            display: 'inline-block', 
                            background: 'var(--color-accent, #E3F2FD)', 
                            padding: '0.25rem 0.5rem', 
                            borderRadius: 'var(--radius-sm)', 
                            margin: '0.25rem 0.25rem 0 0',
                            fontSize: 'var(--font-size-sm)'
                          }}>
                            {loc}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {metadata.entities.emails && metadata.entities.emails.length > 0 && (
                    <div>
                      <strong>Email Addresses:</strong>
                      <div style={{ marginTop: '0.5rem' }}>
                        {metadata.entities.emails.map((email, idx) => (
                          <span key={idx} style={{ 
                            display: 'inline-block', 
                            background: 'var(--color-accent, #FFE0B2)', 
                            padding: '0.25rem 0.5rem', 
                            borderRadius: 'var(--radius-sm)', 
                            margin: '0.25rem 0.25rem 0 0',
                            fontSize: 'var(--font-size-sm)'
                          }}>
                            {email}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {metadata.entities.phone_numbers && metadata.entities.phone_numbers.length > 0 && (
                    <div>
                      <strong>Phone Numbers:</strong>
                      <div style={{ marginTop: '0.5rem' }}>
                        {metadata.entities.phone_numbers.map((phone, idx) => (
                          <span key={idx} style={{ 
                            display: 'inline-block', 
                            background: 'var(--color-accent, #FFE0B2)', 
                            padding: '0.25rem 0.5rem', 
                            borderRadius: 'var(--radius-sm)', 
                            margin: '0.25rem 0.25rem 0 0',
                            fontSize: 'var(--font-size-sm)'
                          }}>
                            {phone}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {metadata.entities.urls && metadata.entities.urls.length > 0 && (
                    <div>
                      <strong>URLs:</strong>
                      <div style={{ marginTop: '0.5rem' }}>
                        {metadata.entities.urls.map((url, idx) => (
                          <span key={idx} style={{ 
                            display: 'inline-block', 
                            background: 'var(--color-accent, #E8F5E8)', 
                            padding: '0.25rem 0.5rem', 
                            borderRadius: 'var(--radius-sm)', 
                            margin: '0.25rem 0.25rem 0 0',
                            fontSize: 'var(--font-size-sm)',
                            wordBreak: 'break-all'
                          }}>
                            {url}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {metadata.entities.dates && metadata.entities.dates.length > 0 && (
                    <div>
                      <strong>Dates:</strong>
                      <div style={{ marginTop: '0.5rem' }}>
                        {metadata.entities.dates.map((date, idx) => (
                          <span key={idx} style={{ 
                            display: 'inline-block', 
                            background: 'var(--color-accent, #FFF3E0)', 
                            padding: '0.25rem 0.5rem', 
                            borderRadius: 'var(--radius-sm)', 
                            margin: '0.25rem 0.25rem 0 0',
                            fontSize: 'var(--font-size-sm)'
                          }}>
                            {date}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Content Analysis */}
            {metadata.content_analysis && typeof metadata.content_analysis === 'object' && (
              <div style={{ marginBottom: '2rem' }}>
                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 500, marginBottom: '1rem', color: 'var(--text-primary)' }}>
                  Content Analysis
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  {metadata.content_analysis.sentiment && (
                    <div>
                      <strong>Sentiment:</strong> {metadata.content_analysis.sentiment}
                    </div>
                  )}
                  {metadata.content_analysis.content_type && (
                    <div>
                      <strong>Content Type:</strong> {metadata.content_analysis.content_type}
                    </div>
                  )}
                  {metadata.content_analysis.reading_level && (
                    <div>
                      <strong>Reading Level:</strong> {metadata.content_analysis.reading_level}
                    </div>
                  )}
                </div>
                {metadata.content_analysis.key_topics && Array.isArray(metadata.content_analysis.key_topics) && metadata.content_analysis.key_topics.length > 0 && (
                  <div style={{ marginTop: '1rem' }}>
                    <strong>Key Topics:</strong>
                    <div style={{ marginTop: '0.5rem' }}>
                      {metadata.content_analysis.key_topics.map((topic, idx) => (
                        <span key={idx} style={{ 
                          display: 'inline-block', 
                          background: 'var(--color-accent, #F3E5F5)', 
                          padding: '0.25rem 0.5rem', 
                          borderRadius: 'var(--radius-sm)', 
                          margin: '0.25rem 0.25rem 0 0',
                          fontSize: 'var(--font-size-sm)'
                        }}>
                          {typeof topic === 'object' && topic && 'topic' in topic ? (topic as any).topic : topic}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Processing Information */}
            {metadata.processing_info && (
              <div style={{ marginBottom: '2rem' }}>
                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 500, marginBottom: '1rem', color: 'var(--text-primary)' }}>
                  Processing Information
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <strong>Extraction Time:</strong> {formatDate(metadata.processing_info.extraction_timestamp)}
                  </div>
                  <div>
                    <strong>Processing Duration:</strong> {metadata.processing_info.processing_time_ms}ms
                  </div>
                  <div>
                    <strong>Method:</strong> {metadata.processing_info.method}
                  </div>
                </div>
              </div>
            )}
            
            {/* Action Buttons */}
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between',
              alignItems: 'center',
              paddingTop: '1rem',
              borderTop: '1px solid var(--border-color, #E5E5E5)'
            }}>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button
                  onClick={() => exportMetadata('json')}
                  className="btn-anthropic btn-anthropic-secondary"
                  style={{
                    padding: '0.75rem 1.5rem',
                    fontSize: 'var(--font-size-sm, 1rem)',
                    fontWeight: 500,
                    borderRadius: 'var(--radius-md, 8px)',
                    transition: 'all 0.2s ease'
                  }}
                  title="Download metadata as JSON file"
                >
                  📄 Export JSON
                </button>
                <button
                  onClick={() => exportMetadata('csv')}
                  className="btn-anthropic btn-anthropic-secondary"
                  style={{
                    padding: '0.75rem 1.5rem',
                    fontSize: 'var(--font-size-sm, 1rem)',
                    fontWeight: 500,
                    borderRadius: 'var(--radius-md, 8px)',
                    transition: 'all 0.2s ease'
                  }}
                  title="Download metadata as CSV file"
                >
                  📊 Export CSV
                </button>
              </div>
              <button
                onClick={() => setShowMetadata(false)}
                className="btn-anthropic btn-anthropic-primary"
                style={{
                  padding: '0.75rem 1.5rem',
                  fontSize: 'var(--font-size-sm, 1rem)',
                  fontWeight: 500,
                  borderRadius: 'var(--radius-md, 8px)',
                  transition: 'all 0.2s ease'
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  // Only re-render if the file data actually changed
  return prevProps.file.id === nextProps.file.id &&
         prevProps.file.status === nextProps.file.status &&
         prevProps.file.filename === nextProps.file.filename &&
         prevProps.file.download_url === nextProps.file.download_url;
});