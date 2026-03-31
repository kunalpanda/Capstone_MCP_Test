import { motion } from 'framer-motion';
import type { ReactNode } from 'react';

interface Props {
  title: string;
  value: string;
  subtitle: string;
  accent?: 'cyan' | 'violet' | 'emerald' | 'amber';
  icon?: ReactNode;
}

export default function KpiCard({ title, value, subtitle, accent = 'cyan', icon }: Props) {
  return (
    <motion.div
      className={`kpi-card accent-${accent}`}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      whileHover={{ y: -4 }}
    >
      <div className="kpi-row">
        <span className="kpi-title">{title}</span>
        <span className="kpi-icon">{icon}</span>
      </div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-subtitle">{subtitle}</div>
    </motion.div>
  );
}
