import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Shield } from 'lucide-react';
import QuarantineList from '../components/Quarantine/QuarantineList';

export const Quarantine: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <Link
              to="/"
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex items-center space-x-3">
              <Shield className="h-8 w-8 text-orange-500" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Quarantine Management</h1>
                <p className="text-sm text-gray-600 mt-1">
                  Manage files that failed processing due to security or format issues
                </p>
              </div>
            </div>
          </div>
        </div>

        <QuarantineList />

        <div className="mt-8 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-start space-x-3">
            <Shield className="h-5 w-5 text-amber-600 mt-0.5" />
            <div className="text-sm text-amber-800">
              <p className="font-medium mb-1">About Quarantined Files</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Files are quarantined when they contain potential security threats or unsupported formats</li>
                <li>These files cannot be processed and should be reviewed before deletion</li>
                <li>Deleted files are permanently removed and cannot be recovered</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};