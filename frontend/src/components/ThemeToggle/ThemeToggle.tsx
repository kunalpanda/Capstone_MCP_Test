// src/components/ThemeToggle/ThemeToggle.tsx
// Animated dark/light mode toggle switch

import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { Theme } from '../../hooks/useTheme';
import './ThemeToggle.css';

interface ThemeToggleProps {
  theme: Theme;
  onToggle: () => void;
  size?: 'sm' | 'md' | 'lg';
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ 
  theme, 
  onToggle,
  size = 'md' 
}) => {
  const isDark = theme === 'dark';
  
  const iconSizes = {
    sm: 14,
    md: 16,
    lg: 18
  };

  return (
    <button
      className={`theme-toggle theme-toggle--${size}`}
      onClick={onToggle}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      <div className="theme-toggle__track">
        <div className={`theme-toggle__thumb ${isDark ? 'theme-toggle__thumb--dark' : ''}`}>
          <div className="theme-toggle__icon theme-toggle__icon--sun">
            <Sun size={iconSizes[size]} strokeWidth={2.5} />
          </div>
          <div className="theme-toggle__icon theme-toggle__icon--moon">
            <Moon size={iconSizes[size]} strokeWidth={2.5} />
          </div>
        </div>
      </div>
      <span className="sr-only">
        {isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      </span>
    </button>
  );
};

export default ThemeToggle;
