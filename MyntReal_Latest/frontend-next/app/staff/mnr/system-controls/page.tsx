"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function SystemControlsPage() {
  return (
    <GenericDataTable 
      title="System Controls"
      endpoint="/staff/mnr/system-controls"
      subtitle="Auto-mapped data viewer for staff/mnr/system-controls"
    />
  );
}
