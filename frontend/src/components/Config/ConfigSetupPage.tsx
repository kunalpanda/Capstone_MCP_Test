import React from 'react';
import { Bot, ShieldCheck, Zap } from 'lucide-react';
import { ConfigForm } from './ConfigForm';
import './ConfigSetupPage.css';

interface ConfigSetupPageProps { onConfigured: () => void; }

export const ConfigSetupPage: React.FC<ConfigSetupPageProps> = ({ onConfigured }) => (
  <div className="config-setup">

    {/* ── Left panel ─────────────────────────────────────── */}
    <div className="config-setup__panel config-setup__panel--left">

      {/* Ambient drifting orbs — pure CSS animation */}
      <div className="config-setup__orb config-setup__orb--1" aria-hidden="true" />
      <div className="config-setup__orb config-setup__orb--2" aria-hidden="true" />

      {/* Brand */}
      <div className="config-setup__brand">
        <div className="config-setup__logo">
          <Bot size={30} />
          <div className="config-setup__logo-ring" aria-hidden="true" />
        </div>
        <h1 className="config-setup__title">Capstone CI/CD</h1>
        <p className="config-setup__subtitle">Autonomous AI-powered pipeline orchestration</p>
      </div>

      {/* Feature list */}
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

    {/* ── Right panel ────────────────────────────────────── */}
    <div className="config-setup__panel config-setup__panel--right">
      {/* Glass card wraps the form for lifted appearance */}
      <div className="config-setup__glass-card">
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
