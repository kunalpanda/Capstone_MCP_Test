import React from 'react';

interface MetricCardProps {
  label: string;
  value: number;
  type?: 'success' | 'error' | 'default';
}

export const MetricCard: React.FC<MetricCardProps> = ({ label, value, type = 'default' }) => {
  return (
    <div className="metric-card">
      <div className={`metric-value ${type}`}>{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
};