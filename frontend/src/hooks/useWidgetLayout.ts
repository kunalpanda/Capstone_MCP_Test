import { useState, useCallback, useEffect } from 'react';

export interface WidgetConfig {
  id: string;
  title: string;
  visible: boolean;
  minWidth?: number;
  minHeight?: number;
}

export interface WidgetLayout {
  widgets: string[]; // Ordered array of widget IDs
  hiddenWidgets: string[]; // IDs of hidden widgets
}

const LAYOUT_STORAGE_KEY = 'orchestrator-widget-layout';

// Default widget configuration
export const DEFAULT_WIDGETS: WidgetConfig[] = [
  { id: 'workflow-status', title: 'Workflow Status', visible: true, minWidth: 300 },
  { id: 'coverage', title: 'Test Coverage', visible: true, minWidth: 300 },
  { id: 'repository', title: 'Repository Info', visible: true, minWidth: 280 },
  { id: 'recent-actions', title: 'Recent Actions', visible: true, minWidth: 280 },
  { id: 'event-stream', title: 'Event Stream', visible: true, minWidth: 400 },
  { id: 'productivity', title: 'Productivity Impact', visible: true, minWidth: 300 },
];

const DEFAULT_LAYOUT: WidgetLayout = {
  widgets: DEFAULT_WIDGETS.map(w => w.id),
  hiddenWidgets: [],
};

const getInitialLayout = (): WidgetLayout => {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(LAYOUT_STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as WidgetLayout;
        // Validate that all default widgets exist in the stored layout
        const allWidgetIds = new Set([...parsed.widgets, ...parsed.hiddenWidgets]);
        const defaultIds = DEFAULT_WIDGETS.map(w => w.id);
        
        // Add any missing widgets
        const missingWidgets = defaultIds.filter(id => !allWidgetIds.has(id));
        if (missingWidgets.length > 0) {
          parsed.widgets = [...parsed.widgets, ...missingWidgets];
        }
        
        // Remove any widgets that no longer exist
        const validIds = new Set(defaultIds);
        parsed.widgets = parsed.widgets.filter(id => validIds.has(id));
        parsed.hiddenWidgets = parsed.hiddenWidgets.filter(id => validIds.has(id));
        
        return parsed;
      } catch (e) {
        console.error('Failed to parse widget layout from localStorage:', e);
      }
    }
  }
  return DEFAULT_LAYOUT;
};

const saveLayout = (layout: WidgetLayout): void => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(layout));
  }
};

interface UseWidgetLayoutReturn {
  layout: WidgetLayout;
  visibleWidgets: string[];
  reorderWidgets: (activeId: string, overId: string) => void;
  toggleWidgetVisibility: (widgetId: string) => void;
  showWidget: (widgetId: string) => void;
  hideWidget: (widgetId: string) => void;
  resetLayout: () => void;
  getWidgetConfig: (widgetId: string) => WidgetConfig | undefined;
}

export const useWidgetLayout = (): UseWidgetLayoutReturn => {
  const [layout, setLayout] = useState<WidgetLayout>(getInitialLayout);

  // Persist layout changes to localStorage
  useEffect(() => {
    saveLayout(layout);
  }, [layout]);

  // Get only visible widgets in order
  const visibleWidgets = layout.widgets.filter(
    id => !layout.hiddenWidgets.includes(id)
  );

  const reorderWidgets = useCallback((activeId: string, overId: string) => {
    setLayout(prev => {
      const oldIndex = prev.widgets.indexOf(activeId);
      const newIndex = prev.widgets.indexOf(overId);

      if (oldIndex === -1 || newIndex === -1 || oldIndex === newIndex) {
        return prev;
      }

      const newWidgets = [...prev.widgets];
      newWidgets.splice(oldIndex, 1);
      newWidgets.splice(newIndex, 0, activeId);

      return {
        ...prev,
        widgets: newWidgets,
      };
    });
  }, []);

  const toggleWidgetVisibility = useCallback((widgetId: string) => {
    setLayout(prev => {
      const isHidden = prev.hiddenWidgets.includes(widgetId);
      
      if (isHidden) {
        return {
          ...prev,
          hiddenWidgets: prev.hiddenWidgets.filter(id => id !== widgetId),
        };
      } else {
        return {
          ...prev,
          hiddenWidgets: [...prev.hiddenWidgets, widgetId],
        };
      }
    });
  }, []);

  const showWidget = useCallback((widgetId: string) => {
    setLayout(prev => ({
      ...prev,
      hiddenWidgets: prev.hiddenWidgets.filter(id => id !== widgetId),
    }));
  }, []);

  const hideWidget = useCallback((widgetId: string) => {
    setLayout(prev => {
      if (prev.hiddenWidgets.includes(widgetId)) {
        return prev;
      }
      return {
        ...prev,
        hiddenWidgets: [...prev.hiddenWidgets, widgetId],
      };
    });
  }, []);

  const resetLayout = useCallback(() => {
    setLayout(DEFAULT_LAYOUT);
  }, []);

  const getWidgetConfig = useCallback((widgetId: string): WidgetConfig | undefined => {
    return DEFAULT_WIDGETS.find(w => w.id === widgetId);
  }, []);

  return {
    layout,
    visibleWidgets,
    reorderWidgets,
    toggleWidgetVisibility,
    showWidget,
    hideWidget,
    resetLayout,
    getWidgetConfig,
  };
};

export default useWidgetLayout;
