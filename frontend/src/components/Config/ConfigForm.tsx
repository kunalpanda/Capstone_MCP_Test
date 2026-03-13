import React, { useState } from 'react';
import { Eye, EyeOff, Save, Loader2, Github, Wrench } from 'lucide-react';
import './ConfigForm.css';

const WEBHOOK_URL = 'https://webhook-handler-389127668230.us-central1.run.app';

interface ConfigFormProps {
  onSuccess: () => void;
  compact?: boolean;
}

interface FormFields {
  github_token: string;
  jenkins_url: string;
  jenkins_user: string;
  jenkins_token: string;
}

const FIELDS = [
  { key: 'github_token'  as const, label: 'GitHub Personal Access Token', placeholder: 'ghp_xxxxxxxxxxxxxxxxxxxx',           isSecret: true,  icon: <Github size={16} />, hint: 'Needs repo and workflow scopes.' },
  { key: 'jenkins_url'   as const, label: 'Jenkins URL',                   placeholder: 'https://jenkins.example.com',       isSecret: false, icon: <Wrench size={16} />, hint: 'Full URL including protocol. No trailing slash.' },
  { key: 'jenkins_user'  as const, label: 'Jenkins Username',              placeholder: 'admin',                             isSecret: false, icon: <Wrench size={16} />, hint: 'The user whose API token is provided below.' },
  { key: 'jenkins_token' as const, label: 'Jenkins API Token',             placeholder: '11xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', isSecret: true,  icon: <Wrench size={16} />, hint: 'Generate in Jenkins -> User -> Configure -> API Token.' },
];

export const ConfigForm: React.FC<ConfigFormProps> = ({ onSuccess, compact = false }) => {
  const [fields, setFields]         = useState<FormFields>({ github_token: '', jenkins_url: '', jenkins_user: '', jenkins_token: '' });
  const [revealed, setRevealed]     = useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]           = useState<string | null>(null);

  const toggle = (key: string) => setRevealed(prev => ({ ...prev, [key]: !prev[key] }));

  const handleChange = (key: keyof FormFields, value: string) => {
    setFields(prev => ({ ...prev, [key]: value }));
    if (error) setError(null);
  };

  const handleSubmit = async () => {
    const empty = FIELDS.filter(f => !fields[f.key].trim()).map(f => f.label);
    if (empty.length > 0) { setError(`Please fill in: ${empty.join(', ')}`); return; }

    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${WEBHOOK_URL}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fields),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as any).detail || `Server error: ${res.status}`);
      }
      onSuccess();
    } catch (e: any) {
      setError(e.message || 'Failed to save. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={`config-form ${compact ? 'config-form--compact' : ''}`}>
      <div className="config-form__fields">
        {FIELDS.map(({ key, label, placeholder, isSecret, icon, hint }) => (
          <div key={key} className="config-form__field">
            <label className="config-form__label">
              <span className="config-form__label-icon">{icon}</span>
              {label}
            </label>
            <div className="config-form__input-wrap">
              <input
                className="config-form__input"
                type={isSecret && !revealed[key] ? 'password' : 'text'}
                placeholder={placeholder}
                value={fields[key]}
                onChange={e => handleChange(key, e.target.value)}
                autoComplete="off"
                spellCheck={false}
              />
              {isSecret && (
                <button type="button" className="config-form__reveal" onClick={() => toggle(key)} title={revealed[key] ? 'Hide' : 'Show'}>
                  {revealed[key] ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              )}
            </div>
            <p className="config-form__hint">{hint}</p>
          </div>
        ))}
      </div>

      {error && <div className="config-form__error" role="alert">{error}</div>}

      <button className="config-form__submit" onClick={handleSubmit} disabled={submitting}>
        {submitting
          ? <><Loader2 size={16} className="animate-spin" /><span>Saving...</span></>
          : <><Save size={16} /><span>Save Configuration</span></>}
      </button>
    </div>
  );
};

export default ConfigForm;