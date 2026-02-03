// src/components/Dashboard/DraggableGrid.tsx
// Drag-and-drop grid container using @dnd-kit

import React, { useState } from 'react';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  MeasuringStrategy,
} from '@dnd-kit/core';
import {
  SortableContext,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable';
import {
  LayoutGrid,
  Eye,
  EyeOff,
  RotateCcw,
  Settings2,
  ChevronDown
} from 'lucide-react';
import { DEFAULT_WIDGETS, WidgetConfig } from '../../hooks/useWidgetLayout';
import './DraggableGrid.css';

interface DraggableGridProps {
  children: React.ReactNode;
  widgetIds: string[];
  hiddenWidgetIds: string[];
  onReorder: (activeId: string, overId: string) => void;
  onToggleWidget: (widgetId: string) => void;
  onResetLayout: () => void;
}

export const DraggableGrid: React.FC<DraggableGridProps> = ({
  children,
  widgetIds,
  hiddenWidgetIds,
  onReorder,
  onToggleWidget,
  onResetLayout,
}) => {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  // Configure sensors for drag detection
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // Minimum drag distance before activation
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      onReorder(active.id as string, over.id as string);
    }

    setActiveId(null);
  };

  const handleDragCancel = () => {
    setActiveId(null);
  };

  // Get widget config by ID
  const getWidgetConfig = (id: string): WidgetConfig | undefined => {
    return DEFAULT_WIDGETS.find(w => w.id === id);
  };

  return (
    <div className="draggable-grid-container">
      {/* Grid Controls */}
      <div className="grid-controls">
        <div className="grid-controls__left">
          <LayoutGrid size={16} />
          <span className="grid-controls__title">Dashboard Widgets</span>
          <span className="grid-controls__count">
            {widgetIds.length - hiddenWidgetIds.length} visible
          </span>
        </div>

        <div className="grid-controls__right">
          {/* Widget Visibility Toggle */}
          <div className="grid-controls__dropdown">
            <button
              className="grid-controls__btn"
              onClick={() => setShowSettings(!showSettings)}
              title="Manage widgets"
            >
              <Settings2 size={16} />
              <span>Widgets</span>
              <ChevronDown size={14} className={showSettings ? 'rotate-180' : ''} />
            </button>

            {showSettings && (
              <div className="grid-controls__menu">
                <div className="grid-controls__menu-header">
                  <span>Toggle Widgets</span>
                </div>
                <div className="grid-controls__menu-items">
                  {DEFAULT_WIDGETS.map(widget => {
                    const isHidden = hiddenWidgetIds.includes(widget.id);
                    return (
                      <button
                        key={widget.id}
                        className={`grid-controls__menu-item ${isHidden ? 'grid-controls__menu-item--hidden' : ''}`}
                        onClick={() => onToggleWidget(widget.id)}
                      >
                        {isHidden ? <EyeOff size={14} /> : <Eye size={14} />}
                        <span>{widget.title}</span>
                      </button>
                    );
                  })}
                </div>
                <div className="grid-controls__menu-footer">
                  <button
                    className="grid-controls__reset-btn"
                    onClick={onResetLayout}
                  >
                    <RotateCcw size={14} />
                    <span>Reset Layout</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Drag and Drop Context */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
        measuring={{
          droppable: {
            strategy: MeasuringStrategy.Always,
          },
        }}
      >
        <SortableContext
          items={widgetIds.filter(id => !hiddenWidgetIds.includes(id))}
          strategy={rectSortingStrategy}
        >
          <div className="draggable-grid">
            {children}
          </div>
        </SortableContext>

        {/* Drag Overlay - Shows preview of dragged item */}
        <DragOverlay adjustScale={false}>
          {activeId ? (
            <div className="drag-overlay">
              <div className="drag-overlay__content">
                <LayoutGrid size={20} />
                <span>{getWidgetConfig(activeId)?.title || 'Widget'}</span>
              </div>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* Click outside to close dropdown */}
      {showSettings && (
        <div
          className="grid-controls__backdrop"
          onClick={() => setShowSettings(false)}
        />
      )}
    </div>
  );
};

export default DraggableGrid;
