"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ProductionResetStatusPage() {
  return (
    <GenericDataTable 
      title="Production Reset Status"
      endpoint="/staff/mnr/production-reset-status"
      subtitle="Auto-mapped data viewer for staff/mnr/production-reset-status"
    />
  );
}
