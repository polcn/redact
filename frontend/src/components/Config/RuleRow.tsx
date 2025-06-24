import React from 'react';
import { Rule } from './ConfigEditor';

interface RuleRowProps {
  rule: Rule;
  onUpdate: (rule: Rule) => void;
  onDelete: () => void;
}

export const RuleRow: React.FC<RuleRowProps> = ({ rule, onUpdate, onDelete }) => {
  return (
    <div className="grid grid-cols-12 gap-2">
      <input
        type="text"
        value={rule.find}
        onChange={(e) => onUpdate({ ...rule, find: e.target.value })}
        placeholder="Text to find"
        className="col-span-5 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm"
      />
      <input
        type="text"
        value={rule.replace}
        onChange={(e) => onUpdate({ ...rule, replace: e.target.value })}
        placeholder="Replacement text"
        className="col-span-5 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm"
      />
      <button
        onClick={onDelete}
        className="col-span-2 inline-flex items-center justify-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    </div>
  );
};