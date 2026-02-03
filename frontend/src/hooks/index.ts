// src/hooks/index.ts
// Barrel export for custom hooks

export { useTheme, initializeTheme } from './useTheme';
export type { Theme } from './useTheme';

export { useWidgetLayout, DEFAULT_WIDGETS } from './useWidgetLayout';
export type { WidgetConfig, WidgetLayout } from './useWidgetLayout';

export { useWebSocket } from './useWebSocket';
export { useOrchestratorState } from './useOrchestratorState';
