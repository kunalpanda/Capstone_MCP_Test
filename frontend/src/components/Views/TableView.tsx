// src/components/Views/TableView.tsx
// Table view for events

import React from 'react';
import { EventTable } from '../EventTable';
import { BaseEvent } from '../../services/types';
import './TableView.css';

interface TableViewProps {
  events: BaseEvent[];
}

export const TableView: React.FC<TableViewProps> = ({ events }) => {
  return (
    <div className="table-view">
      <div className="table-view__main">
        <EventTable events={events} />
      </div>
    </div>
  );
};

export default TableView;
