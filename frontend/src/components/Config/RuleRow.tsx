import React from 'react';
import { Rule } from './ConfigEditor';

interface RuleRowProps {
  rule: Rule;
  onUpdate: (rule: Rule) => void;
  onDelete: () => void;
}

export const RuleRow: React.FC<RuleRowProps> = ({ rule, onUpdate, onDelete }) => {
  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: '1fr 1fr auto',
      gap: 'var(--space-md)',
      alignItems: 'center'
    }}>
      <input
        type="text"
        value={rule.find}
        onChange={(e) => onUpdate({ ...rule, find: e.target.value })}
        placeholder="Text to find"
        className="input-anthropic"
      />
      <input
        type="text"
        value={rule.replace}
        onChange={(e) => onUpdate({ ...rule, replace: e.target.value })}
        placeholder="Replacement text"
        className="input-anthropic"
      />
      <button
        onClick={onDelete}
        className="btn-anthropic"
        style={{ 
          padding: '0.5rem',
          color: '#D64545',
          borderColor: '#D64545',
          minWidth: 'auto'
        }}
        title="Delete rule"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    </div>
  );
};