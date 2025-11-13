import React from 'react';
import { PRSummaryData } from '../services/types';
import './PRSummaryModal.css';
import ReactMarkdown from 'react-markdown';

interface PRSummaryModalProps {
  summary: PRSummaryData | null;
  isOpen: boolean;
  onClose: () => void;
}

export const PRSummaryModal: React.FC<PRSummaryModalProps> = ({ summary, isOpen, onClose }) => {
  if (!isOpen || !summary) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>🎉 Pull Request Created</h2>
        </div>
        
        <div className="modal-body">
          <div className="pr-metadata">
            <div className="pr-info">
              <strong>PR #{summary.pr_number}</strong>
              <span className="branch-badge">{summary.branch}</span>
            </div>
            <a 
              href={summary.pr_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="view-github-link"
            >
              View on GitHub →
            </a>
          </div>
          
          <div className="pr-title">
            <h3>{summary.title}</h3>
          </div>
          
          <div className="pr-body-section">
            <div className="section-label">Claude's Summary:</div>
            <div className="pr-body-content markdown-content">
              <ReactMarkdown>{summary.body}</ReactMarkdown>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="close-button" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};