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
      <div className="flex justify-center" style={{ padding: 'var(--space-3xl)' }}>
        <div className="spinner-anthropic"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="card-anthropic">
        <h2 className="mb-sm" style={{ fontSize: 'var(--font-size-xl)' }}>Redaction Rules</h2>
        <p className="text-secondary mb-xl" style={{ fontSize: 'var(--font-size-sm)', lineHeight: 'var(--line-height-relaxed)' }}>
          Configure the text patterns that will be automatically redacted from your documents. 
          These rules will find and replace sensitive information before processing.
        </p>
        
        {error && (
          <div className="mb-lg p-md" style={{ 
            background: 'rgba(214, 69, 69, 0.1)', 
            border: '1px solid rgba(214, 69, 69, 0.2)',
            borderRadius: 'var(--radius-md)',
            color: '#D64545'
          }}>
            {error}
          </div>
        )}
        
        {success && (
          <div className="mb-lg p-md" style={{ 
            background: 'rgba(82, 163, 115, 0.1)', 
            border: '1px solid rgba(82, 163, 115, 0.2)',
            borderRadius: 'var(--radius-md)',
            color: '#52A373'
          }}>
            {success}
          </div>
        )}

        <div className="mb-xl">
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: '1fr 1fr auto',
            gap: 'var(--space-md)',
            paddingBottom: 'var(--space-md)',
            borderBottom: '1px solid var(--border-color)',
            fontSize: 'var(--font-size-sm)',
            fontWeight: 500,
            color: 'var(--text-secondary)'
          }}>
            <div>Find</div>
            <div>Replace</div>
            <div style={{ width: '80px' }}>Actions</div>
          </div>
          
          <div className="mt-md" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            {config.replacements.map((rule, index) => (
              <RuleRow
                key={index}
                rule={rule}
                onUpdate={(rule) => handleUpdateRule(index, rule)}
                onDelete={() => handleDeleteRule(index)}
              />
            ))}
          </div>
        </div>

        <div className="flex gap-sm">
          <button
            onClick={handleAddRule}
            className="btn-anthropic btn-anthropic-secondary"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Rule
          </button>
          
          {config.replacements.length === 0 && (
            <button
              onClick={() => {
                setConfig({
                  ...config,
                  replacements: [
                    { find: 'John Doe', replace: '[NAME]' },
                    { find: 'jane.doe@example.com', replace: '[EMAIL]' },
                    { find: '555-123-4567', replace: '[PHONE]' },
                    { find: 'Confidential', replace: '[REDACTED]' },
                    { find: 'SSN: 123-45-6789', replace: 'SSN: [REDACTED]' }
                  ]
                });
              }}
              className="btn-anthropic btn-anthropic-accent"
            >
              Add Example Rules
            </button>
          )}
        </div>

        <div className="mt-xl pt-xl" style={{ borderTop: '1px solid var(--border-color)' }}>
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={config.case_sensitive}
              onChange={(e) => setConfig({ ...config, case_sensitive: e.target.checked })}
              className="input-anthropic"
              style={{ width: 'auto', marginRight: 'var(--space-sm)' }}
            />
            <span style={{ fontSize: 'var(--font-size-sm)' }}>Case Sensitive</span>
          </label>
        </div>

        <div className="mt-xl">
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-anthropic btn-anthropic-primary"
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
};