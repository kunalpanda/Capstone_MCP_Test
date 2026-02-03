// src/components/Dashboard/Widget.tsx
// Base draggable widget wrapper component

import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  GripVertical,
  Maximize2,
  Minimize2,
  X
} from 'lucide-react';
import './Widget.css';

interface WidgetProps {
  id: string;
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  onHide?: () => void;
  onExpand?: () => void;
  isExpanded?: boolean;
  headerActions?: React.ReactNode;
  className?: string;
  noPadding?: boolean;
}

/**
 * SortableWidget - Draggable widget with dnd-kit integration
 */
export const Widget: React.FC<WidgetProps> = ({
  id,
  title,
  icon,
  children,
  onHide,
  onExpand,
  isExpanded = false,
  headerActions,
  className = '',
  noPadding = false,
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.8 : 1,
    zIndex: isDragging ? 100 : 'auto',
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`widget ${isDragging ? 'widget--dragging' : ''} ${isExpanded ? 'widget--expanded' : ''} ${className}`}
    >
      {/* Widget Header */}
      <div className="widget__header">
        {/* Drag Handle */}
        <button
          className="widget__drag-handle"
          {...attributes}
          {...listeners}
          aria-label="Drag to reorder"
        >
          <GripVertical size={16} />
        </button>

        {/* Title */}
        <div className="widget__title">
          {icon && <span className="widget__title-icon">{icon}</span>}
          <span className="widget__title-text">{title}</span>
        </div>

        {/* Actions */}
        <div className="widget__actions">
          {headerActions}
          
          {onExpand && (
            <button
              className="widget__action-btn"
              onClick={onExpand}
              title={isExpanded ? 'Minimize' : 'Expand'}
            >
              {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
          )}
          
          {onHide && (
            <button
              className="widget__action-btn widget__action-btn--close"
              onClick={onHide}
              title="Hide widget"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Widget Content */}
      <div className={`widget__content ${noPadding ? 'widget__content--no-padding' : ''}`}>
        {children}
      </div>
    </div>
  );
};

/**
 * StaticWidget - Non-draggable widget for use outside DnD context
 */
export const StaticWidget: React.FC<Omit<WidgetProps, 'id'> & { id?: string }> = ({
  title,
  icon,
  children,
  onHide,
  onExpand,
  isExpanded = false,
  headerActions,
  className = '',
  noPadding = false,
}) => {
  return (
    <div className={`widget ${isExpanded ? 'widget--expanded' : ''} ${className}`}>
      {/* Widget Header */}
      <div className="widget__header">
        {/* Title */}
        <div className="widget__title">
          {icon && <span className="widget__title-icon">{icon}</span>}
          <span className="widget__title-text">{title}</span>
        </div>

        {/* Actions */}
        <div className="widget__actions">
          {headerActions}
          
          {onExpand && (
            <button
              className="widget__action-btn"
              onClick={onExpand}
              title={isExpanded ? 'Minimize' : 'Expand'}
            >
              {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
          )}
          
          {onHide && (
            <button
              className="widget__action-btn widget__action-btn--close"
              onClick={onHide}
              title="Hide widget"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Widget Content */}
      <div className={`widget__content ${noPadding ? 'widget__content--no-padding' : ''}`}>
        {children}
      </div>
    </div>
  );
};

/**
 * WidgetPlaceholder - Shown during drag operations
 */
export const WidgetPlaceholder: React.FC<{ height?: number }> = ({ height = 200 }) => {
  return (
    <div className="widget-placeholder" style={{ minHeight: height }}>
      <div className="widget-placeholder__content">
        Drop here
      </div>
    </div>
  );
};

export default Widget;
