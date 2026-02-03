// src/components/PRSummaryModal/PRSummaryModal.tsx
// Modal for displaying PR summary details

import React, { useEffect } from 'react';
import {
  X,
  GitPullRequest,
  ExternalLink,
  GitBranch,
  User,
  Calendar,
  FileCode,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { PRSummary, PRSummaryData } from '../../services/types';
import './PRSummaryModal.css';

interface PRSummaryModalProps {
  prSummary: PRSummary;
  isOpen: boolean;
  onClose: () => void;
}

export const PRSummaryModal: React.FC<PRSummaryModalProps> = ({
  prSummary,
  isOpen,
  onClose
}) => {
  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Simple markdown-like rendering
  const renderMarkdown = (text: string): string => {
    return text
      // Headers
      .replace(/^### (.*$)/gm, '<h3>$1</h3>')
      .replace(/^## (.*$)/gm, '<h2>$1</h2>')
      .replace(/^# (.*$)/gm, '<h1>$1</h1>')
      // Bold
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Italic
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      // Code blocks
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
      // Inline code
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      // Lists
      .replace(/^\s*[-*]\s+(.*$)/gm, '<li>$1</li>')
      // Links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      // Line breaks
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');
  };

  return (
    <div className="pr-modal__overlay" onClick={onClose}>
      <div className="pr-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="pr-modal__header">
          <div className="pr-modal__header-icon">
            <GitPullRequest size={24} />
          </div>
          <div className="pr-modal__header-info">
            <h2 className="pr-modal__title">{prSummary.title}</h2>
            <div className="pr-modal__meta">
              <span className="pr-modal__number">#{prSummary.pr_number}</span>
              <span className="pr-modal__status pr-modal__status--open">
                <CheckCircle2 size={14} />
                Open
              </span>
            </div>
          </div>
          <button className="pr-modal__close" onClick={onClose} title="Close">
            <X size={20} />
          </button>
        </div>

        {/* Details Bar */}
        <div className="pr-modal__details">
          {(prSummary.head_branch || prSummary.branch) && (
            <div className="pr-modal__detail">
              <GitBranch size={14} />
              <span>{prSummary.head_branch || prSummary.branch}</span>
              <span className="pr-modal__arrow">→</span>
              <span>{prSummary.base_branch || 'main'}</span>
            </div>
          )}
          {prSummary.created_at && (
            <div className="pr-modal__detail">
              <Calendar size={14} />
              <span>{new Date(prSummary.created_at).toLocaleDateString()}</span>
            </div>
          )}
        </div>

        {/* Body */}
        <div className="pr-modal__body">
          <div 
            className="pr-modal__content"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(prSummary.body || 'No description provided.') }}
          />
        </div>

        {/* Footer */}
        <div className="pr-modal__footer">
          {(prSummary.html_url || prSummary.pr_url) && (
            <a
              href={prSummary.html_url || prSummary.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              className="pr-modal__action pr-modal__action--primary"
            >
              <ExternalLink size={16} />
              <span>View on GitHub</span>
            </a>
          )}
          <button className="pr-modal__action pr-modal__action--secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default PRSummaryModal;
