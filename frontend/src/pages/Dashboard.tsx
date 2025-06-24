import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Upload } from '../components/Files/Upload';
import { FileList } from '../components/Files/FileList';
import { useNavigate } from 'react-router-dom';

export const Dashboard: React.FC = () => {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate('/login');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const handleUploadComplete = () => {
    // Force refresh of file list
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold">Document Redaction</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/config')}
                className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                Config
              </button>
              <span className="text-gray-500 text-sm">{user?.signInDetails?.loginId}</span>
              <button
                onClick={handleSignOut}
                className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-medium text-gray-900 mb-4">Upload Document</h2>
              <Upload onUploadComplete={handleUploadComplete} />
            </div>

            <div>
              <h2 className="text-lg font-medium text-gray-900 mb-4">Your Files</h2>
              <FileList key={refreshKey} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};