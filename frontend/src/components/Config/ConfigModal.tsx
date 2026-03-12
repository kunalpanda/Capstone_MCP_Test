import React, { useEffect, useState } from 'react';
import { X, Settings } from 'lucide-react';
import { ConfigForm } from './ConfigForm';
import './ConfigModal.css';

interface ConfigModalProps { isOpen: boolean; onClose: () => void; }

export const ConfigModal: React.FC<ConfigModalProps> = ({ isOpen, onClose }) => {
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    if (isOpen) {
      document.addEventListener('keydown', handler);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handler);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  useEffect(() => { if (isOpen) setSaved(false); }, [isOpen]);

  const handleSuccess = () => {
    setSaved(true);
    setTimeout(() => onClose(), 1400);
  };

  if (!isOpen) return null;

  return (
    <div className="config-modal__overlay" onClick={onClose}>
      <div className="config-modal" onClick={e => e.stopPropagation()}
        role="dialog" aria-modal="true" aria-labelledby="config-modal-title">
        <div className="config-modal__header">
          <div className="config-modal__header-icon"><Settings size={22} /></div>
          <div className="config-modal__header-text">
            <h2 id="config-modal-title" className="config-modal__title">Edit Configuration</h2>
            <p className="config-modal__subtitle">Update your credentials. Changes take effect immediately.</p>
          </div>
          <button className="config-modal__close" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>
        <div className="config-modal__body">
          {saved
            ? <div className="config-modal__success">
                <span className="config-modal__success-icon">✅</span>
                <p>Configuration saved successfully!</p>
              </div>
            : <ConfigForm onSuccess={handleSuccess} compact />}
        </div>
      </div>
    </div>
  );
};

export default ConfigModal;