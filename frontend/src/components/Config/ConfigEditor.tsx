import React, { useState, useEffect } from 'react';
import { getConfig, updateConfig } from '../../services/api';
import { RuleRow } from './RuleRow';

export interface Rule {
  find: string;
  replace: string;
}

export interface Config {
  replacements: Rule[];
  case_sensitive: boolean;
}

export const ConfigEditor: React.FC = () => {
  const [config, setConfig] = useState<Config>({
    replacements: [],
    case_sensitive: false
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setError('');
      const data = await getConfig();
      setConfig(data);
    } catch (err: any) {
      setError('Failed to load configuration');
      console.error('Error loading config:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddRule = () => {
    setConfig({
      ...config,
      replacements: [...config.replacements, { find: '', replace: '' }]
    });
  };

  const handleUpdateRule = (index: number, rule: Rule) => {
    const newReplacements = [...config.replacements];
    newReplacements[index] = rule;
    setConfig({ ...config, replacements: newReplacements });
  };

  const handleDeleteRule = (index: number) => {
    const newReplacements = config.replacements.filter((_, i) => i !== index);
    setConfig({ ...config, replacements: newReplacements });
  };

  const handleSave = async () => {
    setError('');
    setSuccess('');
    setSaving(true);

    try {
      await updateConfig(config);
      setSuccess('Configuration saved successfully!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Redaction Rules</h2>
        
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}
        
        {success && (
          <div className="mb-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
            {success}
          </div>
        )}

        <div className="space-y-2 mb-4">
          <div className="grid grid-cols-12 gap-2 text-sm font-medium text-gray-700 pb-2 border-b">
            <div className="col-span-5">Find</div>
            <div className="col-span-5">Replace</div>
            <div className="col-span-2">Actions</div>
          </div>
          
          {config.replacements.map((rule, index) => (
            <RuleRow
              key={index}
              rule={rule}
              onUpdate={(rule) => handleUpdateRule(index, rule)}
              onDelete={() => handleDeleteRule(index)}
            />
          ))}
        </div>

        <button
          onClick={handleAddRule}
          className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
        >
          <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Rule
        </button>

        <div className="mt-6 pt-6 border-t">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={config.case_sensitive}
              onChange={(e) => setConfig({ ...config, case_sensitive: e.target.checked })}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <span className="ml-2 text-sm text-gray-700">Case Sensitive</span>
          </label>
        </div>

        <div className="mt-6">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
};