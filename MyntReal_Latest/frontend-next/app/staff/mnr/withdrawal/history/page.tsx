"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function HistoryPage() {
  return (
    <GenericDataTable 
      title="History"
      endpoint="/staff/mnr/withdrawal/history"
      subtitle="Auto-mapped data viewer for staff/mnr/withdrawal/history"
    />
  );
}
