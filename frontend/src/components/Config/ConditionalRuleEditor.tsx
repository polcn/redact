import React, { useState } from 'react';
import { ConditionalRule, Rule } from './ConfigEditor';
import { RuleRow } from './RuleRow';

interface ConditionalRuleEditorProps {
  rule: ConditionalRule;
  onUpdate: (rule: ConditionalRule) => void;
  onDelete: () => void;
}

export const ConditionalRuleEditor: React.FC<ConditionalRuleEditorProps> = ({
  rule,
  onUpdate,
  onDelete
}) => {
  const [expanded, setExpanded] = useState(false);

  const handleAddTrigger = () => {
    onUpdate({
      ...rule,
      trigger: {
        ...rule.trigger,
        contains: [...rule.trigger.contains, '']
      }
    });
  };

  const handleUpdateTrigger = (index: number, value: string) => {
    const newContains = [...rule.trigger.contains];
    newContains[index] = value;
    onUpdate({
      ...rule,
      trigger: {
        ...rule.trigger,
        contains: newContains
      }
    });
  };

  const handleDeleteTrigger = (index: number) => {
    onUpdate({
      ...rule,
      trigger: {
        ...rule.trigger,
        contains: rule.trigger.contains.filter((_, i) => i !== index)
      }
    });
  };

  const handleAddReplacement = () => {
    onUpdate({
      ...rule,
      replacements: [...rule.replacements, { find: '', replace: '' }]
    });
  };

  const handleUpdateReplacement = (index: number, replacement: Rule) => {
    const newReplacements = [...rule.replacements];
    newReplacements[index] = replacement;
    onUpdate({
      ...rule,
      replacements: newReplacements
    });
  };

  const handleDeleteReplacement = (index: number) => {
    onUpdate({
      ...rule,
      replacements: rule.replacements.filter((_, i) => i !== index)
    });
  };

  return (
    <div className="card-anthropic" style={{ padding: 'var(--space-lg)' }}>
      <div className="flex items-center justify-between mb-md">
        <div className="flex items-center gap-md">
          <input
            type="checkbox"
            checked={rule.enabled}
            onChange={(e) => onUpdate({ ...rule, enabled: e.target.checked })}
            className="input-anthropic"
            style={{ width: 'auto' }}
          />
          <input
            type="text"
            value={rule.name}
            onChange={(e) => onUpdate({ ...rule, name: e.target.value })}
            placeholder="Rule Name"
            className="input-anthropic"
            style={{ width: '200px' }}
          />
          <button
            onClick={() => setExpanded(!expanded)}
            className="btn-anthropic btn-anthropic-secondary"
            style={{ padding: 'var(--space-sm)' }}
          >
            <svg
              className="h-4 w-4 transition-transform"
              style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
        <button
          onClick={onDelete}
          className="btn-anthropic btn-anthropic-secondary"
          style={{ padding: 'var(--space-sm)' }}
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>

      {expanded && (
        <div className="mt-lg" style={{ paddingLeft: 'var(--space-xl)' }}>
          <div className="mb-lg">
            <h4 className="mb-sm" style={{ fontSize: 'var(--font-size-md)', fontWeight: 500 }}>
              Trigger Words
            </h4>
            <p className="text-secondary mb-md" style={{ fontSize: 'var(--font-size-sm)' }}>
              When any of these words are found in the document, apply the replacements below.
            </p>
            
            <div className="space-y-sm">
              {rule.trigger.contains.map((trigger, index) => (
                <div key={index} className="flex gap-sm">
                  <input
                    type="text"
                    value={trigger}
                    onChange={(e) => handleUpdateTrigger(index, e.target.value)}
                    placeholder="Trigger word or phrase"
                    className="input-anthropic flex-1"
                  />
                  <button
                    onClick={() => handleDeleteTrigger(index)}
                    className="btn-anthropic btn-anthropic-secondary"
                    style={{ padding: 'var(--space-sm)' }}
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
            
            <div className="mt-md flex items-center gap-md">
              <button
                onClick={handleAddTrigger}
                className="btn-anthropic btn-anthropic-secondary"
                style={{ fontSize: 'var(--font-size-sm)' }}
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add Trigger
              </button>
              
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={rule.trigger.case_sensitive}
                  onChange={(e) => onUpdate({
                    ...rule,
                    trigger: {
                      ...rule.trigger,
                      case_sensitive: e.target.checked
                    }
                  })}
                  className="input-anthropic"
                  style={{ width: 'auto', marginRight: 'var(--space-sm)' }}
                />
                <span style={{ fontSize: 'var(--font-size-sm)' }}>Case Sensitive Triggers</span>
              </label>
            </div>
          </div>

          <div className="mt-xl">
            <h4 className="mb-sm" style={{ fontSize: 'var(--font-size-md)', fontWeight: 500 }}>
              Replacements
            </h4>
            <p className="text-secondary mb-md" style={{ fontSize: 'var(--font-size-sm)' }}>
              When triggered, apply these find and replace rules.
            </p>
            
            <div className="space-y-sm">
              {rule.replacements.map((replacement, index) => (
                <RuleRow
                  key={index}
                  rule={replacement}
                  onUpdate={(r) => handleUpdateReplacement(index, r)}
                  onDelete={() => handleDeleteReplacement(index)}
                />
              ))}
            </div>
            
            <button
              onClick={handleAddReplacement}
              className="btn-anthropic btn-anthropic-secondary mt-md"
              style={{ fontSize: 'var(--font-size-sm)' }}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Replacement
            </button>
          </div>
        </div>
      )}
    </div>
  );
};