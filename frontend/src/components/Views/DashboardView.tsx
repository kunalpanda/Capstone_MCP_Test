// src/components/Views/DashboardView.tsx
// Main dashboard view with draggable widgets

import React from 'react';
import {
  Activity,
  Target,
  GitBranch,
  Wrench,
  Radio
} from 'lucide-react';
import { Widget, DraggableGrid } from '../Dashboard';
import {
  WorkflowStatusWidget,
  CoverageWidget,
  RepositoryWidget,
  RecentActionsWidget,
  EventStreamWidget
} from '../Widgets';
import { useWidgetLayout } from '../../hooks';
import { OrchestratorState, BaseEvent } from '../../services/types';
import './DashboardView.css';

interface DashboardViewProps {
  state: OrchestratorState;
  events: BaseEvent[];
  workflowStartTime: number | null;
}

// Widget icon mapping
const WIDGET_ICONS: Record<string, React.ReactNode> = {
  'workflow-status': <Activity size={16} />,
  'coverage': <Target size={16} />,
  'repository': <GitBranch size={16} />,
  'recent-actions': <Wrench size={16} />,
  'event-stream': <Radio size={16} />,
};

export const DashboardView: React.FC<DashboardViewProps> = ({ state, events, workflowStartTime }) => {
  const {
    visibleWidgets,
    layout,
    reorderWidgets,
    toggleWidgetVisibility,
    hideWidget,
    resetLayout,
    getWidgetConfig
  } = useWidgetLayout();

  // Render the content for each widget
  const renderWidgetContent = (widgetId: string) => {
    switch (widgetId) {
      case 'workflow-status':
        return <WorkflowStatusWidget state={state} workflowStartTime={workflowStartTime} />;
      case 'coverage':
        return (
          <CoverageWidget
            currentCoverage={state.currentCoverage}
            targetCoverage={state.targetCoverage}
          />
        );
      case 'repository':
        return <RepositoryWidget state={state} />;
      case 'recent-actions':
        return <RecentActionsWidget actions={state.recentActions} totalActions={state.totalActions} />;
      case 'event-stream':
        return <EventStreamWidget events={events} />;
      default:
        return <div>Unknown widget</div>;
    }
  };

  return (
    <div className="dashboard-view">
      <DraggableGrid
        widgetIds={layout.widgets}
        hiddenWidgetIds={layout.hiddenWidgets}
        onReorder={reorderWidgets}
        onToggleWidget={toggleWidgetVisibility}
        onResetLayout={resetLayout}
      >
        {visibleWidgets.map(widgetId => {
          const config = getWidgetConfig(widgetId);
          if (!config) return null;

          return (
            <Widget
              key={widgetId}
              id={widgetId}
              title={config.title}
              icon={WIDGET_ICONS[widgetId]}
              onHide={() => hideWidget(widgetId)}
              className={widgetId === 'event-stream' ? 'widget--event-stream' : ''}
              internalScroll={widgetId === 'event-stream'}
            >
              {renderWidgetContent(widgetId)}
            </Widget>
          );
        })}
      </DraggableGrid>
    </div>
  );
};

export default DashboardView;
