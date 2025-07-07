import React, { useState } from 'react';
import api from '../../services/api';
import { Config } from './ConfigEditor';

interface RedactionTesterProps {
  config: Config;
}

export const RedactionTester: React.FC<RedactionTesterProps> = ({ config }) => {
  const [testText, setTestText] = useState('');
  const [redactedText, setRedactedText] = useState('');
  const [replacementCount, setReplacementCount] = useState<number | null>(null);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState('');

  const handleTest = async () => {
    if (!testText.trim()) {
      setError('Please enter some text to test');
      return;
    }

    setError('');
    setTesting(true);
    setRedactedText('');
    setReplacementCount(null);

    try {
      const response = await api.post('/api/test-redaction', {
        text: testText,
        config: config
      });
      
      setRedactedText(response.data.redacted_text);
      setReplacementCount(response.data.replacements_made);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to test redaction');
    } finally {
      setTesting(false);
    }
  };

  const handleLoadExample = () => {
    setTestText(`Meeting Notes - Choice Hotels Partnership
Date: January 15, 2024
Attendees: John Doe (john.doe@example.com), Jane Smith
Phone: 555-123-4567

Topics Discussed:
1. Choice Hotels expansion plans
2. Cronos project timeline
3. Confidential pricing at $1,234.56

SSN for verification: 123-45-6789
Credit Card on file: 4532-1234-5678-9012

Next Steps:
- Follow up with Choice regarding contract
- Schedule Cronos demo for next week
- IP Address for server: 192.168.1.100`);
  };

  return (
    <div className="card-anthropic">
      <h3 className="mb-md" style={{ fontSize: 'var(--font-size-lg)' }}>Test Your Configuration</h3>
      <p className="text-secondary mb-lg" style={{ fontSize: 'var(--font-size-sm)', lineHeight: 'var(--line-height-relaxed)' }}>
        Test your redaction rules and see how they will be applied to your documents.
      </p>

      <div className="space-y-lg">
        <div>
          <div className="flex justify-between items-center mb-sm">
            <label htmlFor="test-input" style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>
              Input Text
            </label>
            <button
              onClick={handleLoadExample}
              className="btn-anthropic btn-anthropic-secondary"
              style={{ fontSize: 'var(--font-size-sm)', padding: 'var(--space-xs) var(--space-sm)' }}
            >
              Load Example
            </button>
          </div>
          <textarea
            id="test-input"
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            placeholder="Enter text to test redaction..."
            className="input-anthropic"
            rows={8}
            style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-sm)' }}
          />
        </div>

        {error && (
          <div className="p-md" style={{ 
            background: 'rgba(214, 69, 69, 0.1)', 
            border: '1px solid rgba(214, 69, 69, 0.2)',
            borderRadius: 'var(--radius-md)',
            color: '#D64545',
            fontSize: 'var(--font-size-sm)'
          }}>
            {error}
          </div>
        )}

        <div className="flex justify-center">
          <button
            onClick={handleTest}
            disabled={testing || !testText.trim()}
            className="btn-anthropic btn-anthropic-primary"
          >
            {testing ? (
              <>
                <div className="spinner-anthropic" style={{ width: '16px', height: '16px', marginRight: 'var(--space-sm)' }}></div>
                Testing...
              </>
            ) : (
              <>
                <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                Test Redaction
              </>
            )}
          </button>
        </div>

        {redactedText && (
          <div className="space-y-md">
            <div>
              <div className="flex justify-between items-center mb-sm">
                <label htmlFor="test-output" style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>
                  Redacted Output
                </label>
                {replacementCount !== null && (
                  <span className="text-secondary" style={{ fontSize: 'var(--font-size-sm)' }}>
                    {replacementCount} replacement{replacementCount !== 1 ? 's' : ''} made
                  </span>
                )}
              </div>
              <textarea
                id="test-output"
                value={redactedText}
                readOnly
                className="input-anthropic"
                rows={8}
                style={{ 
                  fontFamily: 'monospace', 
                  fontSize: 'var(--font-size-sm)',
                  background: 'var(--bg-secondary)',
                  cursor: 'default'
                }}
              />
            </div>

            {replacementCount !== null && replacementCount > 0 && (
              <div className="p-md" style={{ 
                background: 'rgba(82, 163, 115, 0.1)', 
                border: '1px solid rgba(82, 163, 115, 0.2)',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--font-size-sm)'
              }}>
                <div style={{ color: '#52A373', fontWeight: 500, marginBottom: 'var(--space-xs)' }}>
                  ✓ Redaction successful
                </div>
                <div className="text-secondary">
                  Your configuration successfully redacted {replacementCount} piece{replacementCount !== 1 ? 's' : ''} of sensitive information.
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};