import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  GitPullRequest,
  ExternalLink,
  GitBranch,
  CheckCircle2,
  FileText
} from 'lucide-react';
import { PRSummaryData } from '../services/types';
import './PRSummaryModal.css';

interface PRSummaryModalProps {
  summary: PRSummaryData | null;
  isOpen: boolean;
  onClose: () => void;
}

const normalizeMarkdown = (input?: string): string => {
  if (!input) return 'No workflow summary available.';

  let text = input.trim();

  // Handle bodies that may arrive with escaped newlines
  if (text.includes('\\n')) {
    text = text.replace(/\\n/g, '\n');
  }

  // Normalize Windows line endings
  text = text.replace(/\r\n/g, '\n');

  // Clean up excessive blank lines
  text = text.replace(/\n{3,}/g, '\n\n');

  return text;
};

export const PRSummaryModal: React.FC<PRSummaryModalProps> = ({
  summary,
  isOpen,
  onClose
}) => {
  const markdownBody = useMemo(() => normalizeMarkdown(summary?.body), [summary?.body]);

  if (!isOpen || !summary) return null;

  return (
    <div className="pr-modal-overlay" onClick={onClose}>
      <div className="pr-modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="pr-modal-header">
          <div className="pr-modal-header__left">
            <div className="pr-modal-header__icon">
              <GitPullRequest size={22} />
            </div>

            <div className="pr-modal-header__text">
              <h2>{summary.title}</h2>

              <div className="pr-modal-header__meta">
                <span className="pr-modal__number">#{summary.pr_number}</span>
                <span className="pr-modal__status">
                  <CheckCircle2 size={14} />
                  Open
                </span>
              </div>
            </div>
          </div>

          <button className="pr-modal-close" onClick={onClose} aria-label="Close modal">
            ×
          </button>
        </div>

        <div className="pr-modal-branchbar">
          <div className="pr-modal-branchbar__item">
            <GitBranch size={14} />
            <span>{summary.branch}</span>
          </div>
        </div>

        <div className="pr-modal-body">
          <div className="pr-modal-section">
            <div className="pr-modal-section__label">
              <FileText size={15} />
              <span>Workflow Output</span>
            </div>

            <div className="pr-readme">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ node, ...props }) => (
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
        </div>

        <div className="pr-modal-footer">
          <a
            href={summary.pr_url}
            target="_blank"
            rel="noopener noreferrer"
            className="pr-modal-github-link"
          >
            <ExternalLink size={16} />
            <span>View on GitHub</span>
          </a>

          <button className="pr-modal-footer__close" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};