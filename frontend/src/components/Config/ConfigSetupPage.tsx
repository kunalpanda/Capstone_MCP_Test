import React from 'react';
import { Bot, ShieldCheck, Zap } from 'lucide-react';
import { ConfigForm } from './ConfigForm';
import './ConfigSetupPage.css';

interface ConfigSetupPageProps { onConfigured: () => void; }

export const ConfigSetupPage: React.FC<ConfigSetupPageProps> = ({ onConfigured }) => (
  <div className="config-setup">
    <div className="config-setup__panel config-setup__panel--left">
      <div className="config-setup__brand">
        <div className="config-setup__logo"><Bot size={36} /></div>
        <h1 className="config-setup__title">Capstone CI/CD</h1>
        <p className="config-setup__subtitle">Autonomous AI-powered pipeline orchestration</p>
      </div>
      <ul className="config-setup__features">
        <li className="config-setup__feature">
          <span className="config-setup__feature-icon"><Zap size={18} /></span>
          <div>
            <strong>Autonomous workflows</strong>
            <p>Claude analyses failures, writes fixes, and opens PRs automatically.</p>
          </div>
        </li>
        <li className="config-setup__feature">
          <span className="config-setup__feature-icon"><ShieldCheck size={18} /></span>
          <div>
            <strong>Secrets stored securely</strong>
            <p>Credentials go directly to GCP Secret Manager, never to the database.</p>
          </div>
        </li>
        <li className="config-setup__feature">
          <span className="config-setup__feature-icon"><Bot size={18} /></span>
          <div>
            <strong>One-time setup</strong>
            <p>Fill in once. Every push to main triggers the pipeline automatically.</p>
          </div>
        </li>
      </ul>
    </div>
    <div className="config-setup__panel config-setup__panel--right">
      <div className="config-setup__form-wrap">
        <div className="config-setup__form-header">
          <h2>Connect your services</h2>
          <p>Provide your GitHub and Jenkins credentials to get started.</p>
        </div>
        <ConfigForm onSuccess={onConfigured} />
      </div>
    </div>
  </div>
);

export default ConfigSetupPage;