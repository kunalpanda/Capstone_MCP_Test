// src/components/Views/TableView.tsx
// Table view for events with detail panel

import React, { useState } from 'react';
import { EventTable } from '../EventTable';
import { DetailPanel } from '../DetailPanel';
import { BaseEvent } from '../../services/types';
import './TableView.css';

interface TableViewProps {
  events: BaseEvent[];
}

export const TableView: React.FC<TableViewProps> = ({ events }) => {
  const [isDetailPanelCollapsed, setIsDetailPanelCollapsed] = useState(false);

  return (
    <div className="table-view">
      <div className="table-view__main">
        <EventTable events={events} />
      </div>
      <DetailPanel
        events={events}
        isCollapsed={isDetailPanelCollapsed}
        onToggleCollapse={() => setIsDetailPanelCollapsed(!isDetailPanelCollapsed)}
      />
    </div>
  );
};

export default TableView;
