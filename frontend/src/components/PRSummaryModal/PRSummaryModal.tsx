// src/components/PRSummaryModal/PRSummaryModal.tsx
// Modal for displaying PR summary details

import React, { useEffect, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  X,
  GitPullRequest,
  ExternalLink,
  GitBranch,
  Calendar,
  CheckCircle2
} from 'lucide-react';
import { PRSummary } from '../../services/types';
import './PRSummaryModal.css';

interface PRSummaryModalProps {
  prSummary: PRSummary;
  isOpen: boolean;
  onClose: () => void;
}

const normalizeMarkdown = (text?: string): string => {
  if (!text || !text.trim()) {
    return 'No description provided.';
  }

  let normalized = text.trim();

  // Convert escaped newlines into real newlines if needed
  normalized = normalized.replace(/\\n/g, '\n');

  // Normalize line endings
  normalized = normalized.replace(/\r\n/g, '\n');

  // Collapse excessive empty lines
  normalized = normalized.replace(/\n{3,}/g, '\n\n');

  return normalized;
};

export const PRSummaryModal: React.FC<PRSummaryModalProps> = ({
  prSummary,
  isOpen,
  onClose
}) => {
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

  const markdownBody = useMemo(() => {
    return normalizeMarkdown(prSummary?.body);
  }, [prSummary?.body]);

  if (!isOpen) return null;

  return (
    <div className="pr-modal__overlay" onClick={onClose}>
      <div className="pr-modal" onClick={(e) => e.stopPropagation()}>
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

        <div className="pr-modal__body">
          <div className="pr-modal__content pr-readme">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ ...props }) => (
                  <a {...props} target="_blank" rel="noopener noreferrer" />
                ),
                code({ inline, className, children, ...props }: any) {
                  if (inline) {
                    return (
                      <code className="pr-readme__inline-code" {...props}>
                        {children}
                      </code>
                    );
                  }

                  return (
                    <pre className="pr-readme__codeblock">
                      <code className={className} {...props}>
                        {children}
                      </code>
                    </pre>
                  );
                }
              }}
            >
              {markdownBody}
            </ReactMarkdown>
          </div>
        </div>

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