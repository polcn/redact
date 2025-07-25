import React, { useState, useEffect } from 'react';
import { getExternalAIKeys, updateExternalAIKeys } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

const ExternalAIKeys: React.FC = () => {
  const { user } = useAuth();
  const [keyStatus, setKeyStatus] = useState<any>(null);
  const [openaiKey, setOpenaiKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [showKeys, setShowKeys] = useState(false);
  const [userRole, setUserRole] = useState<string>('user');

  useEffect(() => {
    loadKeyStatus();
  }, []);

  const loadKeyStatus = async () => {
    try {
      const data = await getExternalAIKeys();
      setKeyStatus(data.key_status);
      setUserRole(data.user_role || 'user');
    } catch (err) {
      console.error('Failed to load key status:', err);
    }
  };

  const handleUpdateKeys = async () => {
    setLoading(true);
    setMessage('');
    setError('');

    try {
      const keysToUpdate: any = {};
      if (openaiKey.trim()) keysToUpdate.openai_key = openaiKey.trim();
      if (geminiKey.trim()) keysToUpdate.gemini_key = geminiKey.trim();

      if (Object.keys(keysToUpdate).length === 0) {
        setError('Please enter at least one API key to update');
        setLoading(false);
        return;
      }

      await updateExternalAIKeys(keysToUpdate);
      setMessage('API keys updated successfully');
      setOpenaiKey('');
      setGeminiKey('');
      setShowKeys(false);
      
      // Reload key status
      await loadKeyStatus();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to update API keys');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">External AI Providers</h2>
      
      <div className="mb-6">
        <p className="text-sm text-gray-600 mb-4">
          Configure API keys to enable OpenAI and Google Gemini models for AI summaries.
        </p>
        
        {keyStatus && (
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <div>
                <span className="font-medium">OpenAI</span>
                {keyStatus.openai.configured ? (
                  <span className="ml-2 text-sm text-green-600">✓ Configured</span>
                ) : (
                  <span className="ml-2 text-sm text-gray-500">Not configured</span>
                )}
              </div>
              {keyStatus.openai.last_updated && (
                <span className="text-xs text-gray-500">
                  Updated: {new Date(keyStatus.openai.last_updated).toLocaleDateString()}
                </span>
              )}
            </div>
            
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <div>
                <span className="font-medium">Google Gemini</span>
                {keyStatus.gemini.configured ? (
                  <span className="ml-2 text-sm text-green-600">✓ Configured</span>
                ) : (
                  <span className="ml-2 text-sm text-gray-500">Not configured</span>
                )}
              </div>
              {keyStatus.gemini.last_updated && (
                <span className="text-xs text-gray-500">
                  Updated: {new Date(keyStatus.gemini.last_updated).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {userRole === 'admin' && (
        <div>
          <button
            onClick={() => setShowKeys(!showKeys)}
            className="mb-4 text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            {showKeys ? 'Hide' : 'Update'} API Keys
          </button>

          {showKeys && (
            <div className="border-t pt-4">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    OpenAI API Key
                  </label>
                  <input
                    type="password"
                    value={openaiKey}
                    onChange={(e) => setOpenaiKey(e.target.value)}
                    placeholder="sk-..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Get your API key from{' '}
                    <a
                      href="https://platform.openai.com/api-keys"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      OpenAI Platform
                    </a>
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Google Gemini API Key
                  </label>
                  <input
                    type="password"
                    value={geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                    placeholder="AIza..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Get your API key from{' '}
                    <a
                      href="https://makersuite.google.com/app/apikey"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      Google AI Studio
                    </a>
                  </p>
                </div>

                {message && (
                  <div className="p-3 bg-green-50 text-green-700 rounded-md text-sm">
                    {message}
                  </div>
                )}

                {error && (
                  <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">
                    {error}
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={handleUpdateKeys}
                    disabled={loading}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Updating...' : 'Update Keys'}
                  </button>
                  <button
                    onClick={() => {
                      setShowKeys(false);
                      setOpenaiKey('');
                      setGeminiKey('');
                      setMessage('');
                      setError('');
                    }}
                    className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {userRole !== 'admin' && (
        <p className="text-sm text-gray-500 italic">
          Admin access required to manage API keys.
        </p>
      )}
    </div>
  );
};

export default ExternalAIKeys;