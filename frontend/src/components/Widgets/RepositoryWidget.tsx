import React from 'react';
import {
  GitBranch,
  Github,
  FolderGit2,
  ExternalLink,
  Copy,
  Check
} from 'lucide-react';
import { OrchestratorState } from '../../services/types';
import './RepositoryWidget.css';

interface RepositoryWidgetProps {
  state: OrchestratorState;
}

export const RepositoryWidget: React.FC<RepositoryWidgetProps> = ({ state }) => {
  const [copied, setCopied] = React.useState<string | null>(null);

  const handleCopy = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(field);
      setTimeout(() => setCopied(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const repoUrl = state.repo ? `https://github.com/${state.repo}` : null;
  const branchUrl = repoUrl && state.branch 
    ? `${repoUrl}/tree/${state.branch}` 
    : null;

  // Parse owner and repo name
  const [owner, repoName] = state.repo ? state.repo.split('/') : ['', ''];

  if (!state.repo) {
    return (
      <div className="repository-widget repository-widget--empty">
        <div className="repository-widget__empty-state">
          <FolderGit2 size={32} />
          <span className="repository-widget__empty-title">No Repository</span>
          <span className="repository-widget__empty-text">
            Repository info will appear when a workflow starts
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="repository-widget">
      {/* Repository Header */}
      <div className="repository-widget__header">
        <div className="repository-widget__icon">
          <Github size={24} />
        </div>
        <div className="repository-widget__title-section">
          <span className="repository-widget__owner">{owner}</span>
          <span className="repository-widget__name">{repoName}</span>
        </div>
        {repoUrl && (
          <a
            href={repoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="repository-widget__link"
            title="Open in GitHub"
          >
            <ExternalLink size={16} />
          </a>
        )}
      </div>

      {/* Repository Details */}
      <div className="repository-widget__details">
        {/* Full Repository Path */}
        <div className="repository-widget__detail">
          <div className="repository-widget__detail-label">
            <FolderGit2 size={14} />
            <span>Repository</span>
          </div>
          <div className="repository-widget__detail-value">
            <span className="repository-widget__detail-text">{state.repo}</span>
            <button
              className="repository-widget__copy-btn"
              onClick={() => handleCopy(state.repo, 'repo')}
              title="Copy repository path"
            >
              {copied === 'repo' ? <Check size={14} /> : <Copy size={14} />}
            </button>
          </div>
        </div>

        {/* Branch */}
        {state.branch && (
          <div className="repository-widget__detail">
            <div className="repository-widget__detail-label">
              <GitBranch size={14} />
              <span>Branch</span>
            </div>
            <div className="repository-widget__detail-value">
              <span className="repository-widget__branch-badge">
                {state.branch}
              </span>
              <button
                className="repository-widget__copy-btn"
                onClick={() => handleCopy(state.branch, 'branch')}
                title="Copy branch name"
              >
                {copied === 'branch' ? <Check size={14} /> : <Copy size={14} />}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="repository-widget__actions">
        {repoUrl && (
          <a
            href={repoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="repository-widget__action"
          >
            <Github size={16} />
            <span>View Repository</span>
          </a>
        )}
        {branchUrl && (
          <a
            href={branchUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="repository-widget__action"
          >
            <GitBranch size={16} />
            <span>View Branch</span>
          </a>
        )}
      </div>
    </div>
  );
};

export default RepositoryWidget;
