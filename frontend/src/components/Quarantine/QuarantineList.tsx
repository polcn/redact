import React, { useState, useEffect } from 'react';
import { 
  AlertCircle, 
  Trash2, 
  RefreshCw,
  AlertTriangle,
  FileX
} from 'lucide-react';
import api from '../../services/api';

interface QuarantineFile {
  id: string;
  filename: string;
  quarantine_filename: string;
  size: number;
  last_modified: string;
  quarantine_reason: string;
}

const QuarantineList: React.FC = () => {
  const [files, setFiles] = useState<QuarantineFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingFile, setDeletingFile] = useState<string | null>(null);
  const [deletingAll, setDeletingAll] = useState(false);

  useEffect(() => {
    loadQuarantineFiles();
  }, []);

  const loadQuarantineFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/quarantine/files');
      setFiles(response.data.files || []);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load quarantine files');
      console.error('Error loading quarantine files:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteFile = async (fileId: string) => {
    if (!window.confirm('Are you sure you want to permanently delete this file?')) {
      return;
    }

    setDeletingFile(fileId);
    try {
      await api.delete(`/quarantine/${encodeURIComponent(fileId)}`);
      setFiles(files.filter(f => f.id !== fileId));
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to delete file');
      console.error('Error deleting file:', err);
    } finally {
      setDeletingFile(null);
    }
  };

  const handleDeleteAll = async () => {
    if (files.length === 0) return;
    
    if (!window.confirm(`Are you sure you want to permanently delete all ${files.length} quarantined files? This action cannot be undone.`)) {
      return;
    }

    setDeletingAll(true);
    try {
      await api.post('/quarantine/delete-all');
      setFiles([]);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to delete all files');
      console.error('Error deleting all files:', err);
    } finally {
      setDeletingAll(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  const getReasonIcon = (reason: string) => {
    if (reason.toLowerCase().includes('virus') || reason.toLowerCase().includes('malware')) {
      return <AlertTriangle className="h-4 w-4 text-red-500" />;
    } else if (reason.toLowerCase().includes('format') || reason.toLowerCase().includes('type')) {
      return <FileX className="h-4 w-4 text-orange-500" />;
    } else {
      return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <AlertTriangle className="h-6 w-6 text-orange-500" />
          <h2 className="text-xl font-semibold text-gray-800">Quarantine Files</h2>
          <span className="text-sm text-gray-500">({files.length} files)</span>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={loadQuarantineFiles}
            className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="h-5 w-5" />
          </button>
          {files.length > 0 && (
            <button
              onClick={handleDeleteAll}
              disabled={deletingAll}
              className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
            >
              <Trash2 className="h-4 w-4" />
              <span>{deletingAll ? 'Deleting...' : 'Delete All'}</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {files.length === 0 ? (
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No quarantined files</p>
          <p className="text-sm text-gray-400 mt-2">
            Files that fail processing due to security or format issues appear here
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-700">File Name</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-700">Reason</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-700">Size</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-700">Quarantined</th>
                <th className="text-center px-4 py-3 text-sm font-medium text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {files.map((file) => (
                <tr key={file.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center space-x-2">
                      {getReasonIcon(file.quarantine_reason)}
                      <span className="text-sm text-gray-800">{file.filename}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-600">{file.quarantine_reason}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-600">{formatFileSize(file.size)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-600">{formatDate(file.last_modified)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center space-x-2">
                      <button
                        onClick={() => handleDeleteFile(file.id)}
                        disabled={deletingFile === file.id}
                        className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Delete file"
                      >
                        {deletingFile === file.id ? (
                          <RefreshCw className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default QuarantineList;